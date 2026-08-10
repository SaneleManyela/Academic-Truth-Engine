import sys
import os
import tempfile
import subprocess
import traceback
import shutil

print('=== ENV ===')
print('sys.executable:', sys.executable)
print('which python:', shutil.which('python'))
print('PATH starts with:', os.environ.get('PATH', '').split(os.pathsep)[:5])
print('sys.path:')
for p in sys.path:
    print('  ', p)

try:
    import ipykernel, jupyter_client, jupyter_core, zmq, tornado, IPython, traitlets
    print('ipykernel', ipykernel.__version__)
    print('jupyter_client', jupyter_client.__version__)
    print('jupyter_core', jupyter_core.__version__)
    print('pyzmq', zmq.__version__)
    print('zmq_c', zmq.zmq_version())
    print('tornado', tornado.version)
    print('IPython', IPython.__version__)
    print('traitlets', traitlets.__version__)
except Exception:
    traceback.print_exc()

try:
    from jupyter_client.kernelspec import KernelSpecManager
    ksm = KernelSpecManager()
    specs = ksm.find_kernel_specs()
    print('find_kernel_specs:', specs)
    name = 'python3'
    spec = ksm.get_kernel_spec(name)
    print('spec.argv:', spec.argv)
    print('resource_dir:', spec.resource_dir)
except Exception:
    traceback.print_exc()

try:
    import json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{}')
        tmp.flush()
        tmp_path = tmp.name
    print('testing direct ipykernel_launcher with file:', tmp_path)
    cmd = ['python', '-m', 'ipykernel_launcher', '-f', tmp_path]
    print('command:', cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=5)
        print('exitcode', p.returncode)
        print('--- STDOUT ---')
        print(out)
        print('--- STDERR ---')
        print(err)
    except subprocess.TimeoutExpired:
        print('timeout expired, killing process')
        p.kill()
        out, err = p.communicate(timeout=3)
        print('exitcode after kill', p.returncode)
        print('--- STDOUT after kill ---')
        print(out)
        print('--- STDERR after kill ---')
        print(err)
finally:
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
