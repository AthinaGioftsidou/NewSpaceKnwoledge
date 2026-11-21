from spaceknowledge.common.refusal import Refusal
from spaceknowledge.common.messages import Request, Response, ItemInfo

r = Refusal("mine gold", "there is no gold here", "mine something else")
print(r.describe())
# r.what = "x"              ← try it: AttributeError (read-only)

req = Request("test-op1", "mine", "ada", "iron", 5)
print(req.action, req.item_id, req.amount)
# Request("test-op1", "mine", "ada", "iron", True)   ← try it: TypeError (bool trap)

ok = Response("test-op1")
no = Response("test-op2", r)
print(ok.ok, no.ok, no.refusal.why)
# Response("x", r, (ItemInfo("a", "b", "c"),))      ← try it: ValueError

from pathlib import Path
from spaceknowledge.common.atomic_json import write_json_atomically
write_json_atomically(Path("scratch/test.json"), {"hello": "world"})
print(Path("scratch/test.json").read_text())