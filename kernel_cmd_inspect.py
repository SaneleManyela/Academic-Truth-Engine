from jupyter_client.kernelspec import KernelSpecManager
import subprocess, os, time, sys, traceback

ksm = KernelSpecManager()
try:
    specs = ksm.find_kernel_specs()
    print('find_kernel_specs:', specs)
    name = 'python3'
    if name not in specs:
        print(f"Kernel '{name}' not found in specs")
        sys.exit(1)
    spec = ksm.get_kernel_spec(name)
    print('spec.argv:', spec.argv)
    print('resource_dir:', spec.resource_dir)
    cmd = spec.argv
    env = os.environ.copy()
    env['PYTHONFAULTHANDLER'] = '1'
    print('running cmd (first 10 args):', cmd[:10])
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    print('started subprocess pid:', p.pid)
    try:
        out, err = p.communicate(timeout=5)
        print('--- STDOUT ---')
        print(out)
        print('--- STDERR ---')
        print(err)
    except subprocess.TimeoutExpired:
        print('process still running after timeout, killing')
        p.kill()
        out, err = p.communicate(timeout=3)
        print('--- STDOUT after kill ---')
        print(out)
        print('--- STDERR after kill ---')
        print(err)
    finally:
        print('exitcode', p.returncode)
except Exception:
    traceback.print_exc()
