import struct, zlib
MAGIC=bytes.fromhex('0e147475674a03fc4a15909dc3377f1b')
def rd_fstr(b,p):
    n=struct.unpack_from('<i',b,p)[0]; p+=4
    if n==0: return '',p,False
    if n>0: return b[p:p+n-1].decode('utf-8' if False else 'latin-1'),p+n,False
    return b[p:p-2*n-2].decode('utf-16-le'),p-2*n,True
def wr_fstr(s,force16=None):
    if s=='': return struct.pack('<i',0)
    try:
        if force16: raise UnicodeEncodeError('x','',0,1,'')
        e=s.encode('ascii')
        return struct.pack('<i',len(e)+1)+e+b'\0'
    except UnicodeEncodeError:
        e=s.encode('utf-16-le')
        return struct.pack('<i',-(len(e)//2+1))+e+b'\0\0'
def parse(b):
    assert b[:16]==MAGIC and b[16]==3
    soff,=struct.unpack_from('<q',b,17); p=25
    nent,nns=struct.unpack_from('<II',b,p); p+=8
    nss=[]
    for _ in range(nns):
        h,=struct.unpack_from('<I',b,p); p+=4
        name,p,_w=rd_fstr(b,p)
        nk,=struct.unpack_from('<I',b,p); p+=4
        keys=[]
        for _ in range(nk):
            kh,=struct.unpack_from('<I',b,p); p+=4
            key,p,_w=rd_fstr(b,p)
            sh,si=struct.unpack_from('<Ii',b,p); p+=8
            keys.append([kh,key,sh,si])
        nss.append([h,name,keys])
    assert p==soff,(p,soff)
    n,=struct.unpack_from('<I',b,p); p+=4
    strs=[]
    for _ in range(n):
        s,p,w=rd_fstr(b,p); rc,=struct.unpack_from('<i',b,p); p+=4
        strs.append([s,rc,w])
    assert p==len(b)
    return dict(nent=nent,ns=nss,strs=strs)
def build(L):
    # rebuild string table from per-key values, dedup in first-use order
    out=bytearray()
    idx={}; table=[]; rcs=[]
    body=bytearray()
    nent=0
    for h,name,keys in L['ns']:
        body+=struct.pack('<I',h)+wr_fstr(name)+struct.pack('<I',len(keys))
        for kh,key,sh,val in keys:
            if val not in idx: idx[val]=len(table); table.append(val); rcs.append(0)
            i=idx[val]; rcs[i]+=1; nent+=1
            body+=struct.pack('<I',kh)+wr_fstr(key)+struct.pack('<Ii',sh,i)
    head_len=16+1+8+8
    soff=head_len+len(body)
    out+=MAGIC+bytes([3])+struct.pack('<q',soff)+struct.pack('<II',nent,len(L['ns']))+body
    out+=struct.pack('<I',len(table))
    for s,rc in zip(table,rcs): out+=wr_fstr(s)+struct.pack('<i',rc)
    return bytes(out)
def to_values(L):
    # replace string index by value
    for ns in L['ns']:
        for k in ns[2]: k[3]=L['strs'][k[3]][0]
    return L
def strcrc32(s):
    # UE FCrc::StrCrc32 with 16-bit TCHAR: each UTF-16 unit fed as 4 bytes LE
    data=b''.join(struct.pack('<I',u) for u in struct.unpack('<%dH'%(len(s.encode('utf-16-le'))//2),s.encode('utf-16-le')))
    return zlib.crc32(data)&0xffffffff
