"""Durable, expiring sessions. Only token hashes are persisted."""
import hashlib,json,time
from .persistence import atomic_json

def records(path):
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        return {k:v for k,v in data.items() if isinstance(v,dict) and isinstance(v.get('expires'),(int,float)) and v['expires']>time.time()}
    except (OSError,ValueError,AttributeError):return {}

def key(token):return hashlib.sha256(token.encode()).hexdigest()

def issue(path,token,account):
    data=records(path);data[key(token)]=dict(account=account,expires=time.time()+86400)
    atomic_json(path,data)

def resolve(path,token):
    if not isinstance(token,str) or len(token)>256:return None
    return records(path).get(key(token),{}).get('account')

def revoke(path,token):
    if not token:return
    data=records(path);data.pop(key(token),None);atomic_json(path,data)
