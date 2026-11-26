"""Fig. 1: the framework as run for the Version 4 results: four stages, one sequential pass, no feedback loops."""
import sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
out=sys.argv[1]
INK="#1f2933"; MUTED="#5b6673"; BLUE="#174f86"; LIGHT="#eef3f8"; LINE="#9fb3c8"; GREY="#f3f4f6"
plt.rcParams.update({"font.family":"DejaVu Sans"})
fig,ax=plt.subplots(figsize=(13,6.9),dpi=200); ax.set_xlim(0,13); ax.set_ylim(0,6.9); ax.axis("off")
def box(x,y,w,h,fc,ec,lw=1.4,r=0.08): ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",fc=fc,ec=ec,lw=lw))
def arrow(x0,x1,y): ax.add_patch(FancyArrowPatch((x0,y),(x1,y),arrowstyle="-|>",mutation_scale=16,lw=1.8,color=INK))
# input
box(0.15,3.6,1.55,1.1,GREY,LINE); ax.text(0.925,4.32,"PDF reports",ha="center",fontsize=10.5,fontweight="bold",color=INK)
ax.text(0.925,3.92,"30 firms, FY2024\n5,952 pages",ha="center",va="center",fontsize=8.3,color=MUTED)
S=[("Phase 1: Planner","Report ingestion\n",["ADE PDF extraction","Section identification","Claim extraction (LLM)","Claim typing"],"6,936 claims\n+ passage pool",""),
   ("Phase 2: Mapper","SDG target mapping\n",["169 SDG targets","Goal screen, then\ntarget match (LLM)","Confidence ≥ 0.5 retained",""],"6,325 mapped claims\n(91.2%)",""),
   ("Phase 3: Scorer","Substantiation scoring\n(Version 4)",["Retrieval: 2 same-section and\n3 cross-section passages","LLM scores S, M, T, E (0–3)\nand labels each passage","3 runs: median score,\nmajority label"],"S, M, T, E and passage labels;\nC = sections with an Extend\npassage; SMTE and SMTEC\n(6,320 claims)",""),
   ("Phase 4: Comparator","Cross-report analysis\n(no LLM)",["Goal frequency and mean SMTE","Firm–goal rules A and B","Sector and claim-type models",""],"Corpus tables\nand figures","")]
x0=2.1; w=2.42; gap=0.33; top=6.45; bot=1.55
for i,(title,sub,items,outp,_) in enumerate(S):
    x=x0+i*(w+gap)
    box(x,bot,w,top-bot,"white",BLUE,1.6)
    box(x,top-0.55,w,0.55,BLUE,BLUE,1.6); ax.text(x+w/2,top-0.275,title,ha="center",va="center",color="white",fontsize=10.5,fontweight="bold")
    ax.text(x+w/2,top-0.92,sub,ha="center",va="center",linespacing=1.25,fontsize=8.2,fontweight="bold",color=INK)
    y=top-1.5
    for it in items:
        if it:
            n=it.count("\n"); ax.text(x+w/2,y-0.09*n,it,ha="center",va="center",fontsize=7.6,color=INK,linespacing=1.25)
            y-=0.36+0.20*n
        else: y-=0.36
    oh=1.25 if i==2 else 0.85
    box(x+0.12,bot+0.12,w-0.24,oh,LIGHT,LINE,1.0,0.06)
    ax.text(x+w/2,bot+0.12+oh-0.17,"OUTPUT",ha="center",va="center",fontsize=7,color=MUTED)
    ax.text(x+w/2,bot+0.12+(oh-0.25)/2,outp,ha="center",va="center",fontsize=7.6,color=INK,linespacing=1.3)
    if i==0: arrow(1.72,x-0.02,4.15)
    else: arrow(x-gap+0.03,x-0.02,4.15)
# held-out evaluation note under phase 3
x3=x0+2*(w+gap)
ax.plot([x3+w/2,x3+w/2],[bot,1.18],color=MUTED,lw=1,ls=(0,(3,3)))
box(x3-2.0,0.62,w+4.0,0.56,"white",MUTED,1.0,0.06)
ax.text(x3+w/2,0.90,"Held-out evaluation: four raters scored 60 claims from the same claim text and passages,\nusing the handbook from which the Version 4 prompt was written",ha="center",va="center",fontsize=7.4,color=INK,linespacing=1.3)
box(0.15,0.08,12.7,0.38,GREY,LINE,1.0,0.05)
ax.text(6.5,0.27,"One sequential pass; no stage calls back to an earlier one.   LLM: GPT-4o (snapshot gpt-4o-2024-08-06)   |   Embeddings: text-embedding-3-small   |   Extraction: LandingAI ADE   |   Plain Python",ha="center",va="center",fontsize=6.6,color=INK)
fig.savefig(out,bbox_inches="tight",facecolor="white",pad_inches=0.08)
