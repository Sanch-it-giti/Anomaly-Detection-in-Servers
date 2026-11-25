"""M4A scope-limited extraction. Never buffer/read the calibration tail.

The public extractor admits only three existing development exports and reads
only their header plus exactly 460 rows. Row labels are checked before the CPU
field is read. No encryption, keys, gzip, archive scan or permission changes.
"""
import csv
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import stat
from math import isfinite

from .development_qualification_v1 import EPOCH, FIELDS, PRIMARY_IDS


def _token(handle, delimiter, limit):
    data=bytearray()
    for _ in range(limit):
        ch=handle.read(1)
        if not ch:raise ValueError("Unexpected EOF in authorized segment")
        data.extend(ch)
        if ch==delimiter:return bytes(data)
    raise ValueError("Oversized/invalid source field")


def read_authorized_rows(handle,start=1152,end=1612):
    """Internal bounded binary reader; no read beyond final authorized newline."""
    if type(start) is not int or type(end) is not int or not 0<=start<end<=1612:
        raise ValueError("Invalid authorized row bounds")
    header=_token(handle,b'\n',256)
    if header.rstrip(b'\r\n')!=','.join(FIELDS).encode():raise ValueError("Unexpected source schema")
    output=bytearray(header);values=[];reasons=[]
    for i in range(start,end):
        timestamp=_token(handle,b',',64)
        seconds=_token(handle,b',',32)
        expected=(i+1)*300
        # Validate labels BEFORE requesting any CPU/quality field. This also
        # avoids reading forbidden CPU if rows were removed/reordered.
        if timestamp!=(EPOCH+timedelta(seconds=expected)).isoformat().encode()+b',' or seconds!=str(expected).encode()+b',':
            raise ValueError("Source index outside the expected authorized position")
        rest=_token(handle,b'\n',4096)
        row=next(csv.reader(io.StringIO((timestamp+seconds+rest).decode())))
        if len(row)!=5:raise ValueError("Unexpected row width")
        value,status,reason=row[2:]
        if status=='valid':
            number=float(value)
            if not isfinite(number) or not 0<=number<=100 or reason:raise ValueError("Invalid genuine measurement")
            values.append(number)
        elif status=='failed' and value=='' and reason:
            values.append(None)
        else:raise ValueError("Missing events must retain original failed-bin status")
        reasons.append(reason)
        output.extend(timestamp+seconds+rest)
    return tuple(values),tuple(reasons),bytes(output)


def extract_development_segment(root,machine,config,output_directory):
    if machine not in PRIMARY_IDS or config['allowed_machine_ids']!=list(PRIMARY_IDS):
        raise ValueError("Only selected development machines admitted")
    if config['new_observations']!=[1152,1612] or config['confirmation_execution_allowed'] is not False:
        raise ValueError("Unauthorized data boundary")
    expected=f'data/processed/dafr/m2b_v1/qualification_20261030_001/development_suffix/{machine}.five_minute.csv'
    source=config['sources'][machine]
    if source['path']!=expected:raise ValueError("Source path changed")
    path=Path(root).resolve()/expected
    if path.resolve()!=path:raise ValueError("Source symlink redirection forbidden")
    before=path.stat()
    if before.st_size!=source['expected_container_bytes']:raise ValueError("Container size differs from recorded M2B export")
    # FileIO is unbuffered and the internal reader requests one byte at a time.
    with path.open('rb',buffering=0) as handle:
        values,reasons,payload=read_authorized_rows(handle)
        consumed=handle.tell()
    after=path.stat()
    fields=('st_ino','st_size','st_mtime_ns','st_mode')
    if any(getattr(before,k)!=getattr(after,k) for k in fields):raise ValueError("Source changed during extraction")
    output_directory=Path(output_directory)
    output_directory.mkdir(parents=True,exist_ok=False)
    with (output_directory/'authorized_1152_1612.csv').open('xb') as out:out.write(payload)
    receipt={'machine_id':machine,'source':expected,'global_index_bounds':[1152,1612],
        'header_plus_rows':461,'bytes_read':consumed,'stopped_before_index':1612,'read_ahead':False,
        'segment_sha256':hashlib.sha256(payload).hexdigest(),'source_mode_unchanged':True,
        'source_stat_before_after':{k:getattr(before,k) for k in fields},
        'recorded_m2b_full_container_sha256':source['recorded_m2b_container_sha256'],
        'full_container_hash_reverified':False,'integrity_scope':'Fresh hash covers only the authorized segment; original whole-export hash is historical provenance',
        'decryption_performed':False,'keys_opened':False,'confirmation_access':False}
    with (output_directory/'extraction_receipt.json').open('x') as out:json.dump(receipt,out,indent=2);out.write('\n')
    return values,reasons,receipt
