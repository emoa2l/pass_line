"""Is the residual deviation noise or bias? Noise shrinks as sqrt(N); bias doesn't."""
import random, math
from validate import run_place_trial, run_oneroll_trial, measure
import craps_math as M
from fractions import Fraction as F

print("Convergence test -- if these are noise, |delta| shrinks with N")
print("=" * 72)
for label, fn, exact in [
    ("Place 4", lambda: run_place_trial(4), float(M.place_edge(4))*100),
    ("Any 7",   lambda: run_oneroll_trial("any7"), float(M.prop_edge(M.P[7], F(4)))*100),
]:
    print(f"\n{label}  (exact {exact:.3f}%)")
    for n in (100_000, 500_000, 2_000_000, 8_000_000):
        sim = measure(fn, trials=n)
        print(f"   N={n:>9,}  sim={sim:7.3f}%  delta={sim-exact:+7.3f}")
