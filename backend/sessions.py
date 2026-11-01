"""Durable local sessions and signed serverless demo sessions."""
import base64,binascii,hashlib,hmac,json,time
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

def issue_signed(account,secret):
    """Issue a portable, expiring session for stateless serverless runtimes."""
    expires=int(time.time()+86400)
    payload=f'{account}.{expires}'.encode()
    signature=hmac.new(secret.encode(),payload,hashlib.sha256).hexdigest().encode()
    return base64.urlsafe_b64encode(payload+b'.'+signature).decode().rstrip('=')

def resolve_signed(token,secret):
    if not isinstance(token,str) or len(token)>512:return None
    try:
        padded=token+'='*(-len(token)%4)
        account,expires,signature=base64.urlsafe_b64decode(padded.encode()).decode().rsplit('.',2)
        payload=f'{account}.{expires}'.encode()
        expected=hmac.new(secret.encode(),payload,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected) or int(expires)<=time.time():return None
        return account
    except (binascii.Error,ValueError,UnicodeDecodeError):return None
