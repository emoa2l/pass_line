import random, statistics, os
from concurrent.futures import ProcessPoolExecutor
from craps_engine import Game
import craps_strategies as S

SPECS=[
    ("440 inside regress, ride 110",  lambda: S.InsideRegress("ride")),
    ("440 inside regress, 3rd hit down", lambda: S.InsideRegress("down")),
    ("ladder trim",                   lambda: S.EricLadder(yo=False, place_410=False, dc=30)),
    ("1c+1dc flat cap100 ($25)",      lambda: S.CappedFlex(unit=25,cap=100,n_come=1,n_dc=1)),
]
def run_one(args):
    i,seed,n=args
    rng=random.Random(seed); nets=[];acts=[];busts=0;troughs=[]
    for _ in range(n):
        g=Game(SPECS[i][1](),bankroll=1000,unit=10,rng=rng,max_rolls=120)
        r=g.run(); t=0
        while g.bets.at_risk()>0 and t<60: g.t.roll(); g.resolve(); t+=1
        nets.append(g.bankroll+g.bets.at_risk()-1000); acts.append(g.action)
        busts+=r["busted"]; troughs.append(r["trough"]-1000)
    return i,nets,acts,busts,troughs
if __name__=="__main__":
    N=5000; jobs=[(i,abs(hash((i,c)))%(2**31),N) for i in range(len(SPECS)) for c in range(8)]
    agg={i:([],[],0,[]) for i in range(len(SPECS))}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i,nets,acts,busts,troughs in ex.map(run_one,jobs):
            a=agg[i]; a[0].extend(nets); a[1].extend(acts); a[3].extend(troughs)
            agg[i]=(a[0],a[1],a[2]+busts,a[3])
    print(f"{8*N:,} sessions x 120 rolls | $1000 bankroll\n")
    print(f"{'strategy':<36}{'mean$':>7}{'med$':>6}{'edge%':>7}{'win%':>6}{'bust%':>6}{'p05':>7}{'p95':>6}{'sd':>5}{'maxDD':>7}")
    print("-"*95)
    for i,(label,_) in enumerate(SPECS):
        nets,acts,busts,troughs=agg[i]; nets.sort(); n=len(nets)
        m=statistics.mean(nets)
        print(f"{label:<36}{m:>7.1f}{nets[n//2]:>6.0f}{-m/statistics.mean(acts)*100:>7.3f}"
              f"{sum(1 for x in nets if x>0)/n*100:>6.1f}{busts/n*100:>6.2f}"
              f"{nets[int(n*.05)]:>7.0f}{nets[int(n*.95)]:>6.0f}{statistics.pstdev(nets):>5.0f}"
              f"{statistics.mean(troughs):>7.0f}")
