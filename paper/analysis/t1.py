import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
FL=[0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7]
NAMES=['hybrid_no_floor']+[f'floor_{f:.2f}' for f in FL]
EF={'nomic':'nomic-embed-text-latest','minilm':'all-minilm-latest','mxbai':'mxbai-embed-large-latest'}
def fname(pref,e):
    return f'sweep-{pref}-{EF[e]}-plain.json' if e=='mxbai' else f'sweep-{pref}-{EF[e]}-plain-kw2.json'
def hitmat(rows,q,names=NAMES): ids=list(rows); return np.array([[retrieval_ext.hit_at_k(rows[i][n],set(q[i]),10) for n in names] for i in ids])
def ndcgmat(rows,q,names=NAMES): ids=list(rows); return np.array([[ndcg_at_k(rows[i][n],q[i],10) for n in names] for i in ids])
def emptymat(rows,names=NAMES): return np.array([[float(len(rows[i][n])==0) for n in names] for i in rows])
def fiqa(off,names=NAMES): return np.array([sum(1 for r in off.values() if not r[n]) for n in names])
def choose(H,tol=0.98):
    m=H.mean(0); q=[f for f,v in zip(FL,m[1:]) if v>=tol*m[0]]; return max(q) if q else None
def ix(f): return 0 if f is None else 1+FL.index(f)
def run(label,calH,E_nd,E_hit,E_empty,F,n_eval,out,seed=0):
    f=choose(calH); j=ix(f)
    d=E_nd[:,j]-E_nd[:,0]; P=pb(d)
    r=dict(label=label,ncal=calH.shape[0],f=f,neval=n_eval,nd0=E_nd[:,0].mean(),ndf=E_nd[:,j].mean(),dnd=P['diff'],lo=P['lo'],hi=P['hi'],p=P['p'],
        hit0=int(E_hit[:,0].sum()),hitf=int(E_hit[:,j].sum()),emp0=int(E_empty[:,0].sum()),empf=int(E_empty[:,j].sum()),fq0=int(F[0]),fqf=int(F[j]),
        nd50=E_nd[:,4].mean(),fq50=int(F[4]),emp50=int(E_empty[:,4].sum()))
    # selection uncertainty
    rng=np.random.default_rng(seed); dn=[];fr=[];cnt={}
    mean_nd=E_nd.mean(0); 
    for _ in range(2000):
        idx=rng.integers(0,calH.shape[0],calH.shape[0]); ff=choose(calH[idx]); jj=ix(ff)
        dn.append(mean_nd[jj]-mean_nd[0]); fr.append(F[jj]); cnt[str(ff)]=cnt.get(str(ff),0)+1
    r['su']=dict(dnd_mean=np.mean(dn),dnd_lo=np.percentile(dn,2.5),dnd_hi=np.percentile(dn,97.5),fq_mean=np.mean(fr),fq_lo=np.percentile(fr,2.5),fq_hi=np.percentile(fr,97.5),
                 share={k:round(v/2000,3) for k,v in sorted(cnt.items())},p_dnd_lt_m001=float(np.mean(np.array(dn)<-0.01)))
    out.append(r); return r
out=[]
for ds,held,cal_tr in (('scifact','scifact-train','train'),('nfcorpus','nfcorpus-dev','dev')):
    tq=qrels_for(ds,'test')
    for e in ('nomic','minilm','mxbai'):
        td=load(fname(ds,e)); T=td['rows']['test']; C=td['rows']['calib']; off=td['rows']['offtopic']
        cq=qrels_for(ds,cal_tr)
        En=ndcgmat(T,tq); Eh=hitmat(T,tq); Ee=emptymat(T); F=fiqa(off)
        # (a)
        run(f'(a) {ds}/{e}: {cal_tr}-100 -> test',hitmat(C,cq),En,Eh,Ee,F,len(T),out)
        if e=='mxbai': continue
        # (b) full held-out -> test
        hd=load(fname(held,e)); hq=qrels_for(ds,'train' if ds=='scifact' else 'dev'); HT=hd['rows']['test']
        H=hitmat(HT,hq)
        run(f'(b) {ds}/{e}: full {cal_tr} ({len(HT)}) -> test',H,En,Eh,Ee,F,len(T),out)
        # (c) calib 100 stored in held-out file -> held-out eval
        calname={'scifact':'test','nfcorpus':'train'}[ds]
        c2q=qrels_for(ds,calname); C2=hd['rows']['calib']
        hEn=ndcgmat(HT,hq); hEh=hitmat(HT,hq); hEe=emptymat(HT); hF=fiqa(hd['rows']['offtopic'])
        run(f'(c) {ds}/{e}: {calname}-100 -> {cal_tr} ({len(HT)})',hitmat(C2,c2q),hEn,hEh,hEe,hF,len(HT),out)
        # file-stored calibrated floor check
for r in out:
    s=r['su']
    print(f"{r['label']} | ncal {r['ncal']} f*={r['f']} | n={r['neval']} | nDCG {r['nd0']:.3f}->{r['ndf']:.3f} d={r['dnd']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}] p={r['p']:.3f} | Hit {r['hit0']}->{r['hitf']}/{r['neval']} | empty {r['emp0']}->{r['empf']} | FiQA {r['fq0']}->{r['fqf']}/300 | f=.50: nDCG {r['nd50']:.3f} empty {r['emp50']} FiQA {r['fq50']}")
    print(f"      selunc: dnDCG mean {s['dnd_mean']:+.4f} [{s['dnd_lo']:+.4f},{s['dnd_hi']:+.4f}] P(d<-0.01)={s['p_dnd_lt_m001']:.3f}; FiQA mean {s['fq_mean']:.1f} [{s['fq_lo']:.0f},{s['fq_hi']:.0f}]; shares {s['share']}")
# mxbai/other stability 5000
print('=== stability 5000')
for ds,cal_tr in (('scifact','train'),('nfcorpus','dev')):
    cq=qrels_for(ds,cal_tr)
    for e in ('nomic','minilm','mxbai'):
        td=load(fname(ds,e)); H=hitmat(td['rows']['calib'],cq); rng=np.random.default_rng(0); cnt={}
        for _ in range(5000):
            idx=rng.integers(0,100,100); k=str(choose(H[idx])); cnt[k]=cnt.get(k,0)+1
        print(ds,e,'file cal',td['summary'].get('calibrated_floor'),'full f*',choose(H),{k:round(v/5000,3) for k,v in sorted(cnt.items())}, 'calib hit curve',[round(float(x),2) for x in H.mean(0)])
