import requests
import json

BASE_URL = 'http://localhost:5000'

def create_policy(deployment_name, namespace, min_replicas, max_replicas, stabilization_period_seconds, scale_up_cpu_percentage, scale_up_period_seconds, scale_down_cpu_percentage, scale_down_period_seconds):
    url = f'{BASE_URL}/policies'
    policy = {
        "deployment": {
            "name": deployment_name,
            "namespace": namespace
        },
        "minReplicas": min_replicas,
        "maxReplicas": max_replicas,
        "stabilizationPeriodSeconds": stabilization_period_seconds,
        "scaleUp": {
            "cpuPercentage": scale_up_cpu_percentage,
            "periodSeconds": scale_up_period_seconds,
        },
        "scaleDown": {
            "cpuPercentage": scale_down_cpu_percentage,
            "periodSeconds": scale_down_period_seconds,
        }
    }
    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(policy))
    return response.json()

def list_deployments():
    url = f'{BASE_URL}/deployments'
    response = requests.get(url)
    return response.json()

def main():
    # Create a policy
    deployment_name = 'nginx-deployment'
    namespace = 'default'
    min_replicas = 1
    max_replicas = 5
    stabilization_period_seconds = 120
    scale_up_cpu_percentage = 70
    scale_up_period_seconds = 60
    scale_down_cpu_percentage = 30
    scale_down_period_seconds = 60

    print("Creating policy...")
    create_response = create_policy(deployment_name, namespace, min_replicas, max_replicas, stabilization_period_seconds, scale_up_cpu_percentage, scale_up_period_seconds, scale_down_cpu_percentage, scale_down_period_seconds)
    print("Policy creation response:", create_response)

    # time.sleep(12)

    # # List deployments
    # print("\nListing deployments...")
    # deployments = list_deployments()
    # print(json.dumps(deployments, indent=2))

if __name__ == '__main__':
    main()