import random, statistics, os
from concurrent.futures import ProcessPoolExecutor
from craps_engine import Game
import craps_strategies as S

SPECS=[("ladder full",(True,True)),("ladder, no yo",(False,True)),
       ("ladder, no 4/10",(True,False)),("ladder, no yo + no 4/10",(False,False))]
def run_one(args):
    i,seed,n=args
    rng=random.Random(seed); nets=[];acts=[];busts=0
    for _ in range(n):
        g=Game(S.EricLadder(*SPECS[i][1]),bankroll=1000,unit=10,rng=rng,max_rolls=120)
        r=g.run(); t=0
        while g.bets.at_risk()>0 and t<60: g.t.roll(); g.resolve(); t+=1
        nets.append(g.bankroll+g.bets.at_risk()-1000); acts.append(g.action); busts+=r["busted"]
    return i,nets,acts,busts
if __name__=="__main__":
    jobs=[(i,abs(hash((i,c)))%(2**31),5000) for i in range(4) for c in range(8)]
    agg={i:([],[],0) for i in range(4)}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i,nets,acts,busts in ex.map(run_one,jobs):
            a=agg[i]; a[0].extend(nets); a[1].extend(acts); agg[i]=(a[0],a[1],a[2]+busts)
    for i,(label,_) in enumerate(SPECS):
        nets,acts,busts=agg[i]; nets.sort(); n=len(nets)
        m=statistics.mean(nets)
        print(f"{label:<26} mean {m:>7.1f}  sd {statistics.pstdev(nets):>4.0f}  "
              f"bust% {busts/n*100:>5.2f}  p05 {nets[int(n*.05)]:>6.0f}  edge% {-m/statistics.mean(acts)*100:.3f}")
