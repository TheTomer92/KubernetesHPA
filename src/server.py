from flask import Flask, request, jsonify
from autoscaler import KubernetesAutoscaler, Policy, ScaleRule
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
autoscaler = KubernetesAutoscaler()

@app.route('/deployments', methods=['GET'])
def list_deployments():
    try:
        response = []
        for deployment_name, status in autoscaler.deployments_status.items():
            response.append({
                "name": deployment_name,
                "namespace": status.namespace,
                "current_replicas": status.current_replicas,
                "current_cpu_average": status.current_cpu_average()
            })
        logging.info("Listed all deployments")
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error listing deployments: {e}")
        return jsonify({"error": "Failed to list deployments"}), 500

@app.route('/policies', methods=['POST'])
def set_policy():
    try:
        data = request.json
        policy = Policy(
            name=data['deployment']['name'],
            namespace=data['deployment']['namespace'],
            min_replicas=data['minReplicas'],
            max_replicas=data['maxReplicas'],
            stabilization_period_seconds=data['stabilizationPeriodSeconds'],
            scale_up=ScaleRule(data['scaleUp']['cpuPercentage'], data['scaleUp']['periodSeconds']),
            scale_down=ScaleRule(data['scaleDown']['cpuPercentage'], data['scaleDown']['periodSeconds'])
        )
        with autoscaler.lock:
            autoscaler.policies[policy.name] = policy
        logging.info(f"Set policy for deployment: {policy.name}")
        return jsonify({"message": "Policy set successfully"}), 201
    except Exception as e:
        logging.error(f"Error setting policy: {e}")
        return jsonify({"error": "Failed to set policy"}), 500

if __name__ == '__main__':
    logging.info("Starting Flask server and autoscaler")
    autoscaler.start_autoscaler()
    app.run(host='0.0.0.0', port=5000)
