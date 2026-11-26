"""Figures 3, 4 and S1 from the frozen Version 4 corpus scores (claims_v4_flat.csv)."""
import sys, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
src, out = sys.argv[1], sys.argv[2]
d=pd.read_csv(src,keep_default_na=False,na_values=['']); d=d[d.complete==1].copy()
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False})
INK="#1f2933"; MUTED="#6b7785"; GRID="#e3e7ec"
SEQ=["#dbe7f3","#9dbfe0","#4d8cc4","#174f86"]
names={"S":"Specificity","M":"Measurability","T":"Temporality","E":"Evidence","C":"Corroboration count (C)"}
# ---- Fig 3: score distribution per dimension
fig,ax=plt.subplots(figsize=(8,3.6),dpi=200)
dims=["S","M","T","E","C"]
for i,k in enumerate(dims):
    left=0
    for lv in range(4):
        p=(d[k]==lv).mean()*100
        ax.barh(i,p,left=left,color=SEQ[lv],edgecolor="white",linewidth=1.5,height=0.62,label=f"Score {lv}" if i==0 else None)
        if p>=6: ax.text(left+p/2,i,f"{p:.0f}%",ha="center",va="center",fontsize=9,color="white" if lv>=2 else INK)
        left+=p
    ax.text(102,i,f"mean {d[k].mean():.2f}",va="center",fontsize=9.5,color=INK)
ax.set_yticks(range(5)); ax.set_yticklabels([names[k] for k in dims],color=INK); ax.invert_yaxis()
ax.axhline(3.5,color=MUTED,lw=0.8,ls=(0,(3,3)))
ax.set_xlim(0,100); ax.set_xlabel("Share of claims (%)",color=MUTED); ax.tick_params(colors=MUTED,length=0)
for s in ("left","bottom"): ax.spines[s].set_color(GRID)
ax.legend(ncol=4,frameon=False,loc="lower left",bbox_to_anchor=(0,1.0),fontsize=9,handlelength=1.2)
fig.tight_layout(); fig.savefig(out+"/fig3_v4.png",bbox_inches="tight",facecolor="white"); plt.close(fig)
# ---- Fig 4: goal frequency x mean SMTE
rows=[]
for g in range(1,18):
    m=d.goals.astype(str).str.split().apply(lambda L:str(g) in L)
    rows.append((g,m.sum(),d.SMTE[m].mean()))
G=pd.DataFrame(rows,columns=["g","n","m"])
fig,ax=plt.subplots(figsize=(7.2,4.8),dpi=200)
xm,ym=G.n.median(),G.m.median()
ax.axvline(xm,color=MUTED,lw=0.8,ls=(0,(3,3))); ax.axhline(ym,color=MUTED,lw=0.8,ls=(0,(3,3)))
ax.scatter(G.n,G.m,s=46,color="#174f86",edgecolor="white",linewidth=1.5,zorder=3)
off={7:(6,4),14:(6,4),13:(6,4),12:(6,4),9:(6,-11),2:(6,-11),3:(-14,-11),11:(6,4),6:(-12,4),15:(6,4),17:(6,-11),16:(6,4),1:(6,4),8:(6,4),4:(-12,4),5:(6,4),10:(6,4)}
for _,r in G.iterrows():
    ax.annotate(str(int(r.g)),(r.n,r.m),xytext=off.get(int(r.g),(6,4)),textcoords="offset points",fontsize=9.5,fontweight="bold",color=INK)
ax.set_xscale("log"); ax.set_xticks([150,300,600,1200,2400]); ax.set_xticklabels(["150","300","600","1,200","2,400"]); ax.minorticks_off(); ax.set_xlabel("Claims mapped to the goal (log scale; a claim counts once for each goal it is mapped to)",color=MUTED,fontsize=9)
ax.set_ylabel("Mean SMTE (0–3)",color=MUTED); ax.tick_params(colors=MUTED); ax.grid(color=GRID,lw=0.6); ax.set_axisbelow(True)
for s in ("left","bottom"): ax.spines[s].set_color(GRID)
yl=ax.get_ylim(); xl=ax.get_xlim()
ax.text(xm*1.03,yl[0]+0.004,f"median {xm:.0f} claims",fontsize=8,color=MUTED,va="bottom")
ax.text(xl[1],ym+0.004,f"median {ym:.2f}",fontsize=8,color=MUTED,ha="right",va="bottom")
fig.tight_layout(); fig.savefig(out+"/fig4_v4.png",bbox_inches="tight",facecolor="white"); plt.close(fig)
G.to_csv(out+"/fig4_data.csv",index=False)
# ---- Fig S1: sector x dimension heatmap
nf=d.groupby("sector").company.nunique()
H=d.groupby("sector")[["S","M","T","E","C","SMTE"]].mean().sort_values("SMTE",ascending=False)
fig,ax=plt.subplots(figsize=(8,4.4),dpi=200)
cols=["S","M","T","E","C","SMTE"]
im=ax.imshow(H[cols].values,cmap="Blues",vmin=0,vmax=3,aspect="auto")
for i in range(H.shape[0]):
    for j,c in enumerate(cols):
        v=H[c].iloc[i]; ax.text(j,i,f"{v:.2f}",ha="center",va="center",fontsize=9,color="white" if v>1.7 else INK,fontweight="bold" if c=="SMTE" else "normal")
ax.set_xticks(range(6)); ax.set_xticklabels(["Specificity","Measurability","Temporality","Evidence","Corroboration\ncount (C)","SMTE"],fontsize=9,color=INK)
ax.set_yticks(range(H.shape[0])); ax.set_yticklabels([f"{s} ({nf[s]} firm{'s' if nf[s]>1 else ''})" for s in H.index],color=INK)
ax.xaxis.tick_top(); ax.tick_params(length=0)
ax.axvline(4.5,color="white",lw=4)
for s in ax.spines.values(): s.set_visible(False)
ax.set_xticks(np.arange(-.5,6,1),minor=True); ax.set_yticks(np.arange(-.5,H.shape[0],1),minor=True); ax.grid(which="minor",color="white",lw=1.5); ax.tick_params(which="minor",length=0)
cb=fig.colorbar(im,ax=ax,orientation="horizontal",fraction=0.05,pad=0.04,aspect=40); cb.set_label("Mean score (0–3)",color=MUTED,fontsize=9); cb.outline.set_visible(False); cb.ax.tick_params(colors=MUTED,labelsize=8)
fig.tight_layout(); fig.savefig(out+"/figS1_v4.png",bbox_inches="tight",facecolor="white"); plt.close(fig)
H.round(3).to_csv(out+"/figS1_data.csv"); print(G.round(3).to_string()); print(H.round(2))
