import os
import sys
import time
import re
import random

# ANSI Colors
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"
C_CYAN = "\033[36m"
C_WHITE = "\033[37m"
C_GRAY = "\033[90m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

# State Machine for Interactive Mode
state = {
    "namespaces": set(),  # e.g., {"f5-ai-sec"}
    "secrets": {},       # namespace -> secret_name (e.g., {"f5-ai-sec": "regcred"})
    "rbac_applied": False,
    "cr_applied": False,
    "operator_running": False,
    "pods": {},          # pod_name -> {"ns": ns, "status": status, "ready": "0/1", "age": 0}
    "step_count": 0
}

def print_slow(text, delay=0.015):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def show_banner():
    banner = f"""
{C_CYAN}{C_BOLD}========================================================================
     _______  _____        _   _    ____ ___ _____ ___ _____   __
    |  ___| ||_   _|      / \ | |  / ___|___|_   _|_ _| ____|  \ \ 
    | |_  | |  | |       / _ \| |  \___ \ | | | |  | ||  _|     \ \ 
    |  _| | |  | |      / ___ \ |___ ___)| |  | |  | || |___    / / 
    |_|   |_|  |_|     /_/   \_\____|____/___||_| |___|_____|  /_/  
                                                                    
         F5 AI Security Offline Deployment Simulator (v1.4.0)
========================================================================{C_RESET}
Welcome to the offline deployment simulator. This tool allows you to:
  1. Learn and practice real Kubernetes commands in an interactive sandbox.
  2. Experience the entire Operator reconciliation lifecycle in Auto-Pilot mode.
  3. Validate offline air-gapped constraints and secret-injection logic.
"""
    print(banner)

def get_pod_list():
    # Helper to generate the list of pods based on current state
    pod_list = []
    
    # 1. Operator Pod (needs cr_applied or helm installed, runs in f5-ai-sec)
    if "f5-ai-sec" in state["namespaces"]:
        if state["cr_applied"] or state["operator_running"]:
            operator_status = "Running"
            operator_ready = "1/1"
            if "f5-ai-sec" not in state["secrets"] or state["secrets"]["f5-ai-sec"] != "regcred":
                operator_status = "ImagePullBackOff"
                operator_ready = "0/1"
            pod_list.append(("f5-ai-security-operator-7c89f57d6-w9kp2", "f5-ai-sec", operator_ready, operator_status, "2m"))

    # 2. If CR is applied, downstream pods are scheduled
    if state["cr_applied"]:
        # Portal / Backend
        if "cai-moderator" in state["namespaces"]:
            db_status = "Running"
            db_ready = "1/1"
            if "cai-moderator" not in state["secrets"] or state["secrets"]["cai-moderator"] != "regcred":
                db_status = "ImagePullBackOff"
                db_ready = "0/1"
            pod_list.append(("cai-moderator-postgres-0", "cai-moderator", db_ready, db_status, "1m"))
            
            portal_status = "Running" if db_status == "Running" else "Pending"
            portal_ready = "1/1" if portal_status == "Running" else "0/1"
            if portal_status == "Running" and ("cai-moderator" not in state["secrets"] or state["secrets"]["cai-moderator"] != "regcred"):
                portal_status = "ImagePullBackOff"
                portal_ready = "0/1"
            pod_list.append(("cai-moderator-portal-58fbc8d94-k98p2", "cai-moderator", portal_ready, portal_status, "45s"))

        # Prefect
        if "prefect" in state["namespaces"]:
            pref_status = "Running"
            pref_ready = "1/1"
            if "prefect" not in state["secrets"] or state["secrets"]["prefect"] != "regcred":
                pref_status = "ImagePullBackOff"
                pref_ready = "0/1"
            pod_list.append(("prefect-server-6789bc45d-l9q23", "prefect", pref_ready, pref_status, "50s"))
            
            # Workflow Worker
            worker_status = "Running" if pref_status == "Running" else "Pending"
            worker_ready = "1/1" if worker_status == "Running" else "0/1"
            if worker_status == "Running" and not state["rbac_applied"]:
                worker_status = "CrashLoopBackOff" # Fails due to lack of RBAC cluster permissions
                worker_ready = "0/1"
            elif worker_status == "Running" and ("prefect" not in state["secrets"] or state["secrets"]["prefect"] != "regcred"):
                worker_status = "ImagePullBackOff"
                worker_ready = "0/1"
            pod_list.append(("cai-workflows-worker-d5fbb5c6-m8s92", "prefect", worker_ready, worker_status, "30s"))

        # Inference
        if "f5-ai-sec-inference" in state["namespaces"]:
            inf_status = "Running"
            inf_ready = "1/1"
            if "f5-ai-sec-inference" not in state["secrets"] or state["secrets"]["f5-ai-sec-inference"] != "regcred":
                inf_status = "ImagePullBackOff"
                inf_ready = "0/1"
            pod_list.append(("cai-moderator-moderator-89dfb67c-n982p", "f5-ai-sec-inference", inf_ready, inf_status, "40s"))
            pod_list.append(("cai-workflows-inference-78fdc9df-v78d2", "f5-ai-sec-inference", inf_ready, inf_status, "35s"))

    return pod_list

def run_auto_pilot():
    print(f"\n{C_MAGENTA}{C_BOLD}🚀 Starting F5 AI Security Auto-Pilot Deployment Orchestration Demo...{C_RESET}")
    time.sleep(1)
    
    # Step 1: Initializing namespaces
    print(f"\n{C_CYAN}[Step 1/6] Initializing isolated namespaces & inject offline image pull secrets...{C_RESET}")
    namespaces = ["f5-ai-sec", "cai-moderator", "f5-ai-sec-inference", "prefect"]
    for ns in namespaces:
        print_slow(f"  $ kubectl create namespace {ns}", 0.005)
        time.sleep(0.3)
        print(f"  {C_GREEN}namespace/{ns} created{C_RESET}")
        
    print_slow("  # Inject docker-registry registry-credentials 'regcred' to bypass air-gapped pre-checks", 0.005)
    for ns in namespaces:
        print_slow(f"  $ kubectl create secret docker-registry regcred -n {ns} --docker-server=harbor.calypsoai.app --docker-username=offline --docker-password=******", 0.002)
        time.sleep(0.2)
        print(f"  {C_GREEN}secret/regcred created in namespace {ns}{C_RESET}")
        
    # Step 2: Establish the RBAC
    print(f"\n{C_CYAN}[Step 2/6] Establish the RBAC authorization for independent Prefect Worker...{C_RESET}")
    print_slow("  $ kubectl apply -f prefect-worker-rbac.yaml", 0.005)
    time.sleep(0.5)
    print(f"  {C_GREEN}clusterrole.rbac.authorization.k8s.io/prefect-worker-role-cai created")
    print(f"  clusterrolebinding.rbac.authorization.k8s.io/prefect-worker-binding-cai created{C_RESET}")

    # Step 3: Deploy Helm Chart and Operator
    print(f"\n{C_CYAN}[Step 3/6] Deploying F5 AI Security Custom Resources Definition & Operator Controller...{C_RESET}")
    print_slow("  $ helm install f5-ai-security-operator ./f5-ai-security-operator-1.4.0.tgz -n f5-ai-sec --set offlineMode=true", 0.005)
    time.sleep(0.8)
    print(f"  {C_GREEN}NAME: f5-ai-security-operator")
    print("  LAST DEPLOYED: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("  NAMESPACE: f5-ai-sec")
    print("  STATUS: deployed")
    print(f"  REVISION: 1{C_RESET}")
    
    print("\n  Spawning Operator Pod...")
    for i in range(3):
        sys.stdout.write(f"\r  [{'.' * (i+1)}{' ' * (2-i)}] Pulling local images from harbor.calypsoai.app...")
        sys.stdout.flush()
        time.sleep(0.5)
    print(f"\r  {C_GREEN}[✔] Operator Pod successfully running in namespace 'f5-ai-sec'{C_RESET}")

    # Step 4: Apply the declaration CR
    print(f"\n{C_CYAN}[Step 4/6] Applying declarative SecurityOperator custom resource...{C_RESET}")
    print_slow("  $ kubectl apply -f f5ai-securityoperator.yaml", 0.005)
    time.sleep(0.6)
    print(f"  {C_GREEN}securityoperator.ai.security.f5.com/f5ai-securityoperator created{C_RESET}")

    # Step 5: Live Operator Reconciliation Loop Simulation
    print(f"\n{C_CYAN}[Step 5/6] Simulating Live Operator Reconciliation Loop...{C_RESET}")
    logs = [
        ("INFO", "Reconciliation triggered by SecurityOperator 'f5ai-securityoperator'"),
        ("INFO", "Validating environment pre-requisites... offlineMode is ENABLED"),
        ("INFO", "Validating imagePullSecrets 'regcred' in target namespaces... OK"),
        ("INFO", "Reconciling Backend DB: launching 'cai-moderator-postgres-0' in 'cai-moderator'"),
        ("INFO", "Database pod running. Seeding initial schema and F5 AI Guardrail default interceptor rules..."),
        ("INFO", "Database seed completed. Deploying 'cai-moderator-portal'..."),
        ("INFO", "Reconciling Workflow plane: deploying Prefect Server 'prefect-server' in 'prefect'"),
        ("INFO", "Prefect API server ready. Injecting RBAC & deploying worker 'cai-workflows-worker'..."),
        ("INFO", "Reconciling Inference plane: detecting cluster GPU resources..."),
        ("INFO", "GPU detected: NVIDIA-A100-SXM4-40GB. Allocation successful."),
        ("INFO", "Deploying Guardrails Engine 'cai-moderator-moderator' in 'f5-ai-sec-inference'"),
        ("INFO", "Deploying Red Team Evaluation models in 'f5-ai-sec-inference'"),
        ("SUCCESS", "Operator reconciliation completed. All planes are healthy and interconnected!")
    ]
    
    for level, msg in logs:
        color = C_GREEN if level == "SUCCESS" else (C_YELLOW if "Reconciling" in msg else C_GRAY)
        time.sleep(0.6)
        print(f"  {C_BOLD}[{level}]{C_RESET} {color}{msg}{C_RESET}")

    # Step 6: Verify deployment status
    print(f"\n{C_CYAN}[Step 6/6] Finalizing: Fetching cluster-wide pod status matrix...{C_RESET}")
    print_slow("  $ kubectl get pods -A", 0.005)
    time.sleep(0.5)
    
    pod_data = [
        ("f5-ai-sec", "f5-ai-security-operator-7c89f57d6-w9kp2", "1/1", "Running", "0", "4m2s"),
        ("cai-moderator", "cai-moderator-postgres-0", "1/1", "Running", "0", "3m15s"),
        ("cai-moderator", "cai-moderator-portal-58fbc8d94-k98p2", "1/1", "Running", "0", "2m45s"),
        ("prefect", "prefect-server-6789bc45d-l9q23", "1/1", "Running", "0", "2m10s"),
        ("prefect", "cai-workflows-worker-d5fbb5c6-m8s92", "1/1", "Running", "0", "1m55s"),
        ("f5-ai-sec-inference", "cai-moderator-moderator-89dfb67c-n982p", "1/1", "Running", "0", "1m30s"),
        ("f5-ai-sec-inference", "cai-workflows-inference-78fdc9df-v78d2", "1/1", "Running", "0", "1m25s")
    ]
    
    print(f"\n  {C_BOLD}{'NAMESPACE':<22} {'NAME':<45} {'READY':<6} {'STATUS':<15} {'RESTARTS':<10} {'AGE':<5}{C_RESET}")
    for ns, name, ready, status, restarts, age in pod_data:
        time.sleep(0.15)
        print(f"  {ns:<22} {name:<45} {ready:<6} {C_GREEN}{status:<15}{C_RESET} {restarts:<10} {age:<5}")

    print(f"\n{C_GREEN}{C_BOLD}🎉 Simulation Completed Successfully!{C_RESET}")
    print("The system is fully operational. Guardrails are actively shielding the LLM gateways, and Red Teaming orchestrations can be triggered via the F5 AI Security Portal.")
    input("\nPress ENTER to return to the main menu...")

def run_interactive_sandbox():
    print(f"\n{C_YELLOW}{C_BOLD}💻 Entering Interactive Kubernetes Sandbox Mode...{C_RESET}")
    print("Type your commands at the prompt. Type 'help' for guidance, or 'exit' to quit.")
    print("Try forgetting some steps (e.g. not injecting secrets or RBAC) to see how K8s reacts!")
    time.sleep(1)

    while True:
        try:
            prompt = f"\n{C_GREEN}{C_BOLD}k8s-master-node ~ %{C_RESET} "
            cmd = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting sandbox...")
            break

        if not cmd:
            continue

        if cmd in ["exit", "quit"]:
            print("Exiting Sandbox Mode...")
            break

        if cmd == "help":
            print(f"""
{C_CYAN}Available simulation commands:{C_RESET}
  • {C_BOLD}kubectl create namespace <ns>{C_RESET} - Create a namespace (e.g., f5-ai-sec, cai-moderator, prefect, f5-ai-sec-inference)
  • {C_BOLD}kubectl get ns{C_RESET} - List all created namespaces
  • {C_BOLD}kubectl create secret docker-registry regcred -n <ns>{C_RESET} - Inject offline registry credential
  • {C_BOLD}kubectl apply -f prefect-worker-rbac.yaml{C_RESET} - Apply cluster RBAC policy for Prefect
  • {C_BOLD}kubectl apply -f f5ai-securityoperator.yaml{C_RESET} - Deploy F5 AI Security custom resource
  • {C_BOLD}kubectl get pods -A{C_RESET} - Check status of all pods across namespaces
  • {C_BOLD}kubectl get pods -n <ns>{C_RESET} - Check status of pods in a specific namespace
  • {C_BOLD}kubectl describe pod <pod-name> -n <ns>{C_RESET} - Inspect detailed events of a pod
  • {C_BOLD}kubectl get securityoperator -n f5-ai-sec{C_RESET} - Show the status of the CR coordinator
  • {C_BOLD}exit{C_RESET} - Return to main menu
""")
            continue

        # Process Commands
        # 1. Create NS
        ns_match = re.match(r"^kubectl\s+create\s+(namespace|ns)\s+(\S+)", cmd)
        if ns_match:
            ns = ns_match.group(2)
            valid_namespaces = {"f5-ai-sec", "cai-moderator", "f5-ai-sec-inference", "prefect"}
            if ns in valid_namespaces:
                if ns in state["namespaces"]:
                    print(f"Error from server (AlreadyExists): namespaces \"{ns}\" already exists")
                else:
                    state["namespaces"].add(ns)
                    print(f"namespace/{ns} created")
            else:
                print(f"Error: Namespace '{ns}' is not in the F5 AI Security deployment architecture plan. Valid namespaces: f5-ai-sec, cai-moderator, prefect, f5-ai-sec-inference.")
            continue

        # 2. Get NS
        if cmd in ["kubectl get ns", "kubectl get namespaces"]:
            print(f"{C_BOLD}{'NAME':<25} {'STATUS':<15} {'AGE':<5}{C_RESET}")
            print(f"{'default':<25} {'Active':<15} {'100d':<5}")
            print(f"{'kube-system':<25} {'Active':<15} {'100d':<5}")
            for ns in sorted(list(state["namespaces"])):
                print(f"{ns:<25} {'Active':<15} {'2m':<5}")
            continue

        # 3. Create Secret
        secret_match = re.match(r"^kubectl\s+create\s+secret\s+docker-registry\s+(\S+)\s+-n\s+(\S+)(.*)", cmd)
        if secret_match:
            secret_name = secret_match.group(1)
            ns = secret_match.group(2)
            if ns not in state["namespaces"]:
                print(f"Error from server (NotFound): namespaces \"{ns}\" not found")
            elif secret_name != "regcred":
                print(f"Error: Secret name must be 'regcred' as specified in the SecurityOperator configuration spec.")
            else:
                state["secrets"][ns] = secret_name
                print(f"secret/{secret_name} created")
            continue

        # 4. Apply Prefect RBAC
        if cmd == "kubectl apply -f prefect-worker-rbac.yaml":
            state["rbac_applied"] = True
            print(f"clusterrole.rbac.authorization.k8s.io/prefect-worker-role-cai created")
            print(f"clusterrolebinding.rbac.authorization.k8s.io/prefect-worker-binding-cai created")
            continue

        # 5. Apply SecurityOperator CR
        if cmd == "kubectl apply -f f5ai-securityoperator.yaml":
            if "f5-ai-sec" not in state["namespaces"]:
                print("Error from server (NotFound): namespaces \"f5-ai-sec\" not found (Must initialize f5-ai-sec namespace before applying CRD controllers)")
            else:
                state["cr_applied"] = True
                print("securityoperator.ai.security.f5.com/f5ai-securityoperator created")
                print(f"{C_YELLOW}[Operator System Logging]{C_RESET} Operator reconciliation loop starting...")
                time.sleep(1)
                # Show live reconcile brief
                if "f5-ai-sec" not in state["secrets"] or state["secrets"]["f5-ai-sec"] != "regcred":
                    print(f"{C_RED}[Operator Warning]{C_RESET} Fails to pull controller images. Namespace 'f5-ai-sec' is missing imagePullSecret 'regcred'!")
                else:
                    print(f"{C_GREEN}[Operator Info]{C_RESET} Operator initialized successfully. Allocating pods based on CR blueprint...")
            continue

        # 6. Get securityoperator
        if cmd in ["kubectl get securityoperator -n f5-ai-sec", "kubectl get securityoperator"]:
            if not state["cr_applied"]:
                print("No resources found in f5-ai-sec namespace.")
            else:
                status = "Ready"
                # Check issues
                reasons = []
                if len(state["namespaces"]) < 4:
                    status = "Progressing"
                    reasons.append("Waiting for all namespaces to initialize")
                if len(state["secrets"]) < 4:
                    status = "Degraded"
                    reasons.append("ImagePullSecrets missing in some planes")
                if not state["rbac_applied"]:
                    status = "Degraded"
                    reasons.append("Prefect ClusterRole binding missing")
                
                print(f"{C_BOLD}{'NAME':<25} {'STATUS':<15} {'AGE':<5}{C_RESET}")
                if status == "Ready":
                    print(f"{'f5ai-securityoperator':<25} {C_GREEN}{'Healthy':<15}{C_RESET} {'3m':<5}")
                else:
                    print(f"{'f5ai-securityoperator':<25} {C_YELLOW}{status:<15}{C_RESET} {'3m':<5}")
                    print(f"  ⤷ Reason: {', '.join(reasons)}")
            continue

        # 7. Get Pods
        pods_match = re.match(r"^kubectl\s+get\s+(pods|pod|po)(.*)", cmd)
        if pods_match:
            args = pods_match.group(2).strip()
            pod_list = get_pod_list()
            
            # Filter if -n was specified
            ns_filter = None
            ns_m = re.search(r"-n\s+(\S+)", args)
            if ns_m:
                ns_filter = ns_m.group(1)
                if ns_filter not in state["namespaces"] and ns_filter != "default":
                    print(f"Error from server (NotFound): namespaces \"{ns_filter}\" not found")
                    continue
            
            all_flag = "-A" in args or "--all-namespaces" in args
            
            if not all_flag and not ns_filter:
                print("No resources found in default namespace. (F5 AI Security components run in f5-ai-sec, cai-moderator, prefect, f5-ai-sec-inference. Use -A or -n to view)")
                continue
                
            filtered_pods = []
            for pod in pod_list:
                if all_flag or (ns_filter and pod[1] == ns_filter):
                    filtered_pods.append(pod)
            
            if not filtered_pods:
                print("No resources found.")
                continue
                
            if all_flag:
                print(f"{C_BOLD}{'NAMESPACE':<22} {'NAME':<45} {'READY':<6} {'STATUS':<18} {'AGE':<5}{C_RESET}")
                for ns, name, ready, status_str, age in filtered_pods:
                    s_color = C_GREEN if status_str == "Running" else (C_RED if "BackOff" in status_str else C_YELLOW)
                    print(f"{ns:<22} {name:<45} {ready:<6} {s_color}{status_str:<18}{C_RESET} {age:<5}")
            else:
                print(f"{C_BOLD}{'NAME':<45} {'READY':<6} {'STATUS':<18} {'AGE':<5}{C_RESET}")
                for name, ns, ready, status_str, age in filtered_pods:
                    s_color = C_GREEN if status_str == "Running" else (C_RED if "BackOff" in status_str else C_YELLOW)
                    print(f"{name:<45} {ready:<6} {s_color}{status_str:<18}{C_RESET} {age:<5}")
            continue

        # 8. Describe Pod
        describe_match = re.match(r"^kubectl\s+describe\s+pod\s+(\S+)\s+-n\s+(\S+)", cmd)
        if describe_match:
            pod_name = describe_match.group(1)
            ns = describe_match.group(2)
            
            # Check if pod exists
            pod_list = get_pod_list()
            matched_pod = None
            for p in pod_list:
                if p[0] == pod_name and p[1] == ns:
                    matched_pod = p
                    break
                    
            if not matched_pod:
                print(f"Error from server (NotFound): pods \"{pod_name}\" not found")
                continue
                
            status_str = matched_pod[3]
            print(f"Name:         {pod_name}")
            print(f"Namespace:    {ns}")
            print(f"Status:       {status_str}")
            print(f"IP:           10.244.2.45")
            print("Containers:")
            print("  cai-component:")
            print("    Image:      harbor.calypsoai.app/calypsoai/f5ai-security-moderator:v1.4.0")
            print("    State:      " + ("Running" if status_str == "Running" else "Waiting"))
            if status_str == "ImagePullBackOff":
                print("      Reason:   ImagePullBackOff")
            elif status_str == "CrashLoopBackOff":
                print("      Reason:   CrashLoopBackOff")
            print("Events:")
            if status_str == "ImagePullBackOff":
                print(f"  {C_RED}Warning  Failed     3m (x4 over 4m)   kubelet  Failed to pull image \"harbor.calypsoai.app/...\": rpc error: code = Unknown desc = failed to pull and unpack image: failed to resolve reference \"harbor.calypsoai.app/...\" failed to authorize: failed to fetch oauth token: 401 Unauthorized{C_RESET}")
                print(f"  {C_RED}Warning  Failed     3m (x4 over 4m)   kubelet  Error: ImagePullBackOff{C_RESET}")
                print(f"  {C_YELLOW}Normal   BackOff    2m (x8 over 4m)   kubelet  Back-off pulling image \"harbor.calypsoai.app/...\"{C_RESET}")
            elif status_str == "CrashLoopBackOff" and "worker" in pod_name:
                print(f"  {C_RED}Warning  Failed     1m (x5 over 2m)   kubelet  Container failed with exit code 1{C_RESET}")
                print(f"  {C_GRAY}Log: Fail to list Namespaces/Pods at cluster scope. Prefect worker lacks system permissions. Did you apply the prefect Cluster-RBAC policy?{C_RESET}")
            else:
                print("  Normal   Scheduled  4m                default-scheduler  Successfully assigned pod to node-1")
                print("  Normal   Pulling    4m                kubelet            Successfully pulled image")
                print("  Normal   Created    3m                kubelet            Created container")
                print("  Normal   Started    3m                kubelet            Started container")
            continue

        # Fallback
        print(f"Command '{cmd}' not recognized or simulated. Type 'help' for valid Kubernetes commands.")

def main():
    while True:
        if sys.platform != 'win32':
            os.system('clear')
        else:
            os.system('cls')
            
        show_banner()
        print("Please choose an option:")
        print(f"  [{C_GREEN}1{C_RESET}] Practice in Kubernetes Interactive Sandbox (Manual Mode)")
        print(f"  [{C_GREEN}2{C_RESET}] Watch Auto-Pilot Deployment Orchestration (Demonstration Mode)")
        print(f"  [{C_GREEN}3{C_RESET}] Exit")
        
        choice = input(f"\n{C_BOLD}Select (1/2/3):{C_RESET} ").strip()
        
        if choice == '1':
            # Reset state for sandbox
            state["namespaces"] = set()
            state["secrets"] = {}
            state["rbac_applied"] = False
            state["cr_applied"] = False
            state["operator_running"] = False
            run_interactive_sandbox()
        elif choice == '2':
            run_auto_pilot()
        elif choice == '3':
            print("\nThank you for using the F5 AI Security Deployment Simulator. Good luck with your deployment! 👋")
            break
        else:
            print(f"{C_RED}Invalid option. Please enter 1, 2, or 3.{C_RESET}")
            time.sleep(1)

if __name__ == '__main__':
    main()
