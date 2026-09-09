def note(a,b,pressure,ref):
    order={"逃げ":0,"逃げ候補":1,"先行":2,"中団":3,"差し":4,"追込":5}; pair="×".join(sorted([str(a),str(b)],key=lambda x:order.get(x,9)))
    z=ref[(ref["先行圧力区分_v1"]==pressure)&(ref["無方向_脚質ペア"]==pair)]
    if not len(z): return "参考データなし"
    r=z.iloc[0]; return f"参考: 安定度{r.get('安定度','-')} / 同時好走率 {float(r.get('ワイド成立率',0))*100:.1f}%"
