import gc
import hashlib
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path

root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root));gc.disable()
from agent_observer.working_set_policy import SampleClock,combine_membership,recent_activity

def kleene_or(a,b):return True if a is True or b is True else False if a is False and b is False else None
def kleene_and(a,b):return False if a is False or b is False else True if a is True and b is True else None
unions=[]
for e,a,r in itertools.product([False,None,True],repeat=3):
    expected=kleene_and(e,kleene_or(a,r));actual=combine_membership(e,a,r).decision
    assert actual is expected;unions.append([e,a,r,actual])
assert combine_membership(True,True,None).decision is True
assert combine_membership(True,False,None).decision is None
assert combine_membership(None,False,False).decision is False
floor_checks=0
for start in range(400,404):
    for elapsed in range(0,33):
        sample=start+elapsed
        for accept_delay in [0,1,4,17]:
            upper=sample+accept_delay
            for fraction in range(4):
                wall=4000+fraction
                for age in [0,1,9,10,11,40]:
                    true_cutoff=sample+40-(wall-4*(1000-age))
                    dlo=start//4+10-age-1;dhi=upper//4+10-age+1
                    for n in sorted({upper//4,dlo-1,dlo,dhi-1,dhi,dhi+1}):
                        if n<upper//4:continue
                        if n<dlo:assert 4*n+3<true_cutoff
                        elif n>=dhi:assert 4*n>=true_cutoff
                        floor_checks+=1
translations=0
for offset in [-10**9,-12345,0,98765,10**9]:
    for native_sample in [10000,1000000]:
        for ttl in [1,10,100,10000]:
            for loss in [0,1,9,99]:
                e=native_sample+ttl;h=e+offset-loss
                for deadline in [native_sample-100,native_sample,native_sample+1,e-1,e,e+100]:
                    cutoff=h-max(0,e-deadline)
                    assert cutoff<=deadline+offset and cutoff<=h;translations+=1
negative={'nativeExpiry':500,'nativeNegativeCutoff':400,'translatedExpiry':450}
negative['unsafeNegativeAt']=450-max(0,500-400);assert negative['unsafeNegativeAt']==350<400
# All support/clock input integers fit the existing safe-integer envelope.
# The proposed R1 output deadline bound is nevertheless exceeded by the model.
maximum=2**53-1;l=maximum-10000;u=l+10;n=l+100;expiry=maximum-1
sid='00000000-0000-4000-8000-000000000001';bid='00000000-0000-4000-8000-000000000002';sample_id='00000000-0000-4000-8000-000000000003'
support={'serviceId':sid,'provider':'codex','namespace':'fixture','contextGeneration':1,'component':'runtime','accepted':1,'sampledBoottimeMs':l,'expiresBoottimeMs':expiry}
source={'provider':'codex','namespace':'fixture','contextGeneration':1,'components':[{'name':'runtime','health':'current','accepted':1,'sampledBoottimeMs':l,'expiresBoottimeMs':expiry}]}
clock=SampleClock(sample_id,'runtime',sid,'codex','fixture',1,bid,'fixture-boottime',l,1700000000000,u)
activity={'at':1699999999000,'source':'codex_turn_metadata','health':'current'}
result=recent_activity(activity,support,clock,source,service_id=sid,boot_id=bid,clock_domain='fixture-boottime',now_boottime_ms=n,expected_sample_id=sample_id)
assert result.decision is True and result.deadline_lower_boottime_ms>maximum and result.deadline_upper_boottime_ms>maximum
range_mismatch={'maximum':maximum,'L':l,'U':u,'now':n,'receiptExpiry':expiry,'wall':clock.wall_ms,'activityAt':activity['at'],'windowMs':259200000,
    'contractExpected':'unknown with no usable out-of-range cutoff','actualDecision':result.decision,'actualReason':result.reason,
    'actualDlo':result.deadline_lower_boottime_ms,'actualDhi':result.deadline_upper_boottime_ms}
loaded={}
for module in tuple(sys.modules.values()):
    path=getattr(module,'__file__',None)
    if path and Path(path).suffix=='.py':
        p=Path(path).resolve()
        if p.is_relative_to(root):loaded[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps({'python':sys.version.split()[0],'gcDisabled':not gc.isenabled(),'unionChecks':len(unions),'flooredCutoffChecks':floor_checks,
    'offsetTranslationChecks':translations,'negativeCounterexample':negative,'rangeMismatch':range_mismatch,
    'coverageClarificationCases':[[True,True,None,'selected even with unknown age'],[False,None,None,'excluded kind needs no age proof'],[True,False,False,'zero-window/negative branches can prove outside']],
    'loadedInputs':loaded,'scope':'Independent arithmetic/client logic only; no source capture, native/profile/runtime/consumer acceptance'},indent=2,sort_keys=True))
