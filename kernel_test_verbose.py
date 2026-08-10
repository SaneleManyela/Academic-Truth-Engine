import logging
import sys
import os
import time
import traceback
import subprocess

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
for n in ('jupyter_client','jupyter_core','traitlets','asyncio','ipykernel'):
    logging.getLogger(n).setLevel(logging.DEBUG)

print('=== ENV ===')
print('python', sys.version)
print('executable', sys.executable)
print('cwd', os.getcwd())
print('sys.path:')
for p in sys.path:
    print('  ', p)

try:
    from jupyter_client import KernelManager
    print('KernelManager imported')
    km = KernelManager()
    print('kernel_spec name:', getattr(km, 'kernel_name', None))
    print('kernel_spec repr:', getattr(km, 'kernel_spec', None))
    print('starting kernel with default pipes...')
    # start kernel (KernelManager handles pipes internally)
    km.start_kernel()
    proc = getattr(km, 'kernel', None)
    print('kernel process object:', proc)
    pid = getattr(proc, 'pid', None)
    print('kernel pid:', pid)

    # try to set non-blocking on stderr/stdout if possible
    def set_nonblocking(fobj):
        try:
            fd = fobj.fileno()
            os.set_blocking(fd, False)
            return True
        except Exception as e:
            print('set_nonblocking failed:', e)
            return False

    if proc is not None:
        # proc may be a Popen object exposing stdout/stderr
        if hasattr(proc, 'stderr') and proc.stderr:
            set_nonblocking(proc.stderr)
        if hasattr(proc, 'stdout') and proc.stdout:
            set_nonblocking(proc.stdout)

    # start client and run a simple command
    kc = km.client()
    kc.start_channels()
    time.sleep(0.5)
    print('sending execute')
    msg_id = kc.execute("print('hello from kernel')")
    print('msg_id', msg_id)
    try:
        reply = kc.get_shell_msg(timeout=5)
        print('shell reply status:', reply['content'].get('status'))
        print('shell reply content keys:', list(reply['content'].keys()))
    except Exception as e:
        print('get_shell_msg exception:', type(e), e)

    # read any available stderr/stdout
    def drain_stream(sname, stream):
        try:
            if stream is None:
                print(f'{sname} is None')
                return
            out = b''
            while True:
                try:
                    chunk = stream.read()
                except BlockingIOError:
                    break
                except Exception as e:
                    print(f'{sname} read exception:', e)
                    break
                if not chunk:
                    break
                out += chunk
            if out:
                print(f'---- {sname} ----')
                try:
                    print(out.decode('utf-8', errors='replace'))
                except Exception:
                    print(out)
        except Exception as e:
            print('drain_stream failed for', sname, e)

    time.sleep(0.5)
    drain_stream('stderr', getattr(proc, 'stderr', None))
    drain_stream('stdout', getattr(proc, 'stdout', None))

    kc.stop_channels()
    km.shutdown_kernel()
    print('shutdown ok')

except Exception:
    traceback.print_exc()
