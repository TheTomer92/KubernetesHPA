# HPA
Implementation of a Kubernetes Horizontal Pod Autoscaler (HPA).

This project implements a simplified version of a Kubernetes Horizontal Pod Autoscaler (HPA) using Python and the Flask framework. The autoscaler monitors the CPU utilization of pods in a deployment and adjusts the number of replicas based on defined policies.

## Features

- Monitor deployments and pods in a Kubernetes cluster
- Scale up or down the number of replicas based on CPU utilization
- Define policies for scaling operations
- API endpoints to manage deployments and policies

## Prerequisites

- Python 3.8 or higher
- Flask
- Requests
- Kubernetes cluster with Metrics Server installed
- kubeconfig file to access the Kubernetes cluster

## Setup

1. **Clone the repository:**

   ```sh
   git clone https://github.com/yourusername/kubernetes-hpa.git
   cd kubernetes-hpa
