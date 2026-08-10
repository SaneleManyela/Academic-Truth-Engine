import traceback, time
from jupyter_client.manager import start_new_kernel

try:
    km, kc = start_new_kernel()
    print("started pid", km.kernel.pid)
    kc.start_channels()
    msg_id = kc.execute("print('hello from kernel')")
    print("msg id", msg_id)
    reply = kc.get_shell_msg(timeout=5)
    print("shell status", reply['content'].get('status'))
    kc.stop_channels()
    km.shutdown_kernel()
    print("shutdown ok")
except Exception:
    traceback.print_exc()
