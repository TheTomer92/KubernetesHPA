import requests
from datetime import datetime, timedelta
import time
import threading
import json
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Policy:
    def __init__(self, name: str, namespace: str, min_replicas: int, max_replicas: int, stabilization_period_seconds: int, scale_up: 'ScaleRule', scale_down: 'ScaleRule'):
        self.name = name
        self.namespace = namespace
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.stabilization_period_seconds = stabilization_period_seconds
        self.scale_up = scale_up
        self.scale_down = scale_down

class ScaleRule:
    def __init__(self, cpu_percentage: float, period_seconds: int):
        self.cpu_percentage = cpu_percentage
        self.period_seconds = period_seconds

class DeploymentStatus:
    def __init__(self, name: str, namespace: str, current_replicas: int, last_scaled_time: datetime, cpu_usage_history: List[float]):
        self.name = name
        self.namespace = namespace
        self.current_replicas = current_replicas
        self.last_scaled_time = last_scaled_time
        self.cpu_usage_history = cpu_usage_history

    def current_cpu_average(self) -> float:
        if not self.cpu_usage_history:
            return 0.0
        return sum(self.cpu_usage_history) / len(self.cpu_usage_history)

class KubernetesAutoscaler:
    KUBERNETES_API_URL = "http://localhost:8001"

    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.deployments_status: Dict[str, DeploymentStatus] = {}
        self.lock = threading.Lock()

    def get_deployment(self, deployment_name: str, namespace: str) -> Dict:
        url = f"{self.KUBERNETES_API_URL}/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error getting deployment {deployment_name}: {e}")
            return {}

    def get_pods(self, namespace: str) -> Dict:
        url = f"{self.KUBERNETES_API_URL}/api/v1/namespaces/{namespace}/pods"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error getting pods for namespace {namespace}: {e}")
            return {}

    def get_pod_metrics(self, namespace: str, pod_name: str) -> Dict:
        url = f"{self.KUBERNETES_API_URL}/apis/metrics.k8s.io/v1beta1/namespaces/{namespace}/pods/{pod_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error getting metrics for pod {pod_name}: {e}")
            return {}

    def get_container_cpu_usage(self, pod_metrics: Dict) -> float:
        try:
            container = pod_metrics['containers'][0]
            cpu_usage_nano_cores = container['usage']['cpu']
            return int(cpu_usage_nano_cores.rstrip('n')) / 1e9  # Convert nano-cores to cores
        except (KeyError, IndexError, ValueError) as e:
            logging.error(f"Error parsing CPU usage: {e}")
            return 0.0

    def get_container_cpu_limit(self, pod: Dict) -> float:
        try:
            container = pod['spec']['containers'][0]
            cpu_limit = container['resources']['limits']['cpu']
            if 'm' in cpu_limit:
                return int(cpu_limit.rstrip('m')) / 1000  # Convert milli-cores to cores
            return float(cpu_limit)
        except (KeyError, IndexError, ValueError) as e:
            logging.error(f"Error parsing CPU limit: {e}")
            return 0.0

    def update_deployment_replicas(self, deployment_name: str, namespace: str, replicas: int) -> Dict:
        url = f"{self.KUBERNETES_API_URL}/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}/scale"
        scale = {
            "spec": {
                "replicas": replicas
            }
        }
        try:
            response = requests.put(url, headers={'Content-Type': 'application/json'}, data=json.dumps(scale))
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error updating replicas for deployment {deployment_name}: {e}")
            return {}

    def scale_deployment(self, deployment_name: str, namespace: str, policy: Policy):
        logging.info(f"Checking scale conditions for deployment: {deployment_name}")
        deployment = self.get_deployment(deployment_name, namespace)
        if not deployment:
            return

        current_replicas = deployment['spec']['replicas']
        current_time = datetime.now()

        pods = self.get_pods(namespace)
        if not pods:
            return

        cpu_usage_list = []
        for pod in pods['items']:
            if pod['metadata']['name'].startswith(deployment_name):
                pod_metrics = self.get_pod_metrics(namespace, pod['metadata']['name'])
                if pod_metrics:
                    cpu_usage_list.append(self.get_container_cpu_usage(pod_metrics))

        if not cpu_usage_list:
            logging.info(f"No pods found for deployment: {deployment_name}")
            return

        with self.lock:
            if deployment_name not in self.deployments_status:
                self.deployments_status[deployment_name] = DeploymentStatus(deployment_name, namespace, current_replicas, current_time, [])

            deployment_status = self.deployments_status[deployment_name]
            deployment_status.cpu_usage_history.append(sum(cpu_usage_list) / len(cpu_usage_list) * 100) # Convert to percentage
            if len(deployment_status.cpu_usage_history) > policy.scale_up.period_seconds:
                deployment_status.cpu_usage_history.pop(0)

            average_cpu_usage = sum(deployment_status.cpu_usage_history) / len(deployment_status.cpu_usage_history)

            # if stabilization time passed
            if (current_time - deployment_status.last_scaled_time).seconds >= policy.stabilization_period_seconds:

                # scale up
                if average_cpu_usage > policy.scale_up.cpu_percentage and current_replicas < policy.max_replicas:             
                    logging.info(f"Scaling up deployment: {deployment_name}")
                    self.update_deployment_replicas(deployment_name, namespace, current_replicas + 1)
                    deployment_status.last_scaled_time = current_time

                # scale down
                elif average_cpu_usage < policy.scale_down.cpu_percentage and current_replicas > policy.min_replicas:
                    logging.info(f"Scaling down deployment: {deployment_name}")
                    self.update_deployment_replicas(deployment_name, namespace, current_replicas - 1)
                    deployment_status.last_scaled_time = current_time

            self.deployments_status[deployment_name] = deployment_status

    def monitor_deployments(self):
        while True:
            policy_list = []
            with self.lock:
                policy_list = list(self.policies.items())

            for policy_name, policy in policy_list:
                try:
                    self.scale_deployment(policy.name, policy.namespace, policy)
                except Exception as e:
                    logging.error(f"Error in scaling deployment {policy.name}: {e}")
            time.sleep(10)

    def start_autoscaler(self):
        logging.info("Starting autoscaler monitoring thread")
        monitor_thread = threading.Thread(target=self.monitor_deployments)
        monitor_thread.start()
