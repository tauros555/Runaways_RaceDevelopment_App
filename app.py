
def _load_local_racecard():
    try:
        rc = load_training_judgment_racecard(config.RACECARD_FILE)
        st.session_state["_racecard_df"] = rc
        return rc
    except Exception as e:
        st.error(f"data/調教判定表.csv の読込に失敗しました: {e}")
        return None

def _render_local_race_selector():
    rc = st.session_state.get("_racecard_df")
    if rc is None:
        rc = _load_local_racecard()
    if rc is None or rc.empty:
        return None

    races = available_races(rc)
    options = []
    label_to_key = {}
    for _, r in races.iterrows():
        label = f"{int(r['年月日'])} {r['場所']} {int(r['R'])}R {r['レース名']} {r['芝・ダ']}{int(r['距離'])}m"
        options.append(label)
        label_to_key[label] = r["current_race_key"]

    selected_label = st.selectbox("対象レース", options)
    race = select_race(rc, label_to_key[selected_label])
    st.caption(f"data/調教判定表.csv を参照中｜出走馬 {len(race)}頭")
    return race


import pandas as pd, streamlit as st
import config
from modules.gdrive_oauth_storage import GoogleDriveOAuthStorage
from modules.history_store import read_csv_auto,load_history,upsert_annual,save_history
from modules.runaway_input import read_runaway_file
from modules.feature_engine import build_features
from modules.simulator_engine import predict,assign_grade
from modules.pair_reference import note
from modules.scenario_engine import predict_scenario,scenario_adjustment
from modules.queue_visual import render_flow
from modules.monte_carlo import simulate_race
from modules.movement_visual import add_movement_columns,render_movement_table,render_movement_flow

st.set_page_config(page_title=config.APP_NAME,page_icon="🏇",layout="wide")
@st.cache_data(show_spinner=False)
def course(): return pd.read_csv(config.COURSE_FILE,encoding="cp932",low_memory=False)
@st.cache_data(show_spinner=False)
def thresholds(): return pd.read_csv(config.THRESHOLD_FILE,encoding="cp932",low_memory=False)
@st.cache_data(show_spinner=False)
def pairref(): return pd.read_csv(config.PAIR_REFERENCE_FILE,encoding="cp932",low_memory=False)
@st.cache_data(show_spinner="履歴マスタ読込中...")
def history(): return load_history(config.HISTORY_FILE,config.SEED_HISTORY_FILE)
def course_row(place,surface,distance):
    c=course(); surf="芝" if surface=="芝" else "ダート"
    z=c[(c["場所"].astype(str)==str(place))&(c["芝・ダート"].astype(str)==surf)&(pd.to_numeric(c["距離"],errors="coerce")==float(distance))]
    return z.iloc[0].to_dict() if len(z) else {}

gdrive=GoogleDriveOAuthStorage(st.secrets,st.session_state)

def handle_gdrive_oauth_callback():
    try:
        code=st.query_params.get("code")
        if isinstance(code,list): code=code[0] if code else None
        if code and not st.session_state.get("_gdrive_oauth_code_done"):
            gdrive.exchange_code(code)
            st.session_state["_gdrive_oauth_code_done"]=True
            st.session_state["_gdrive_msg"]="Google Drive認証が完了しました。"
            try: st.query_params.clear()
            except Exception: pass
    except Exception as e:
        st.session_state["_gdrive_msg"]=f"OAuth認証処理失敗: {e}"

def sync_history_from_drive_once():
    if st.session_state.get("_gdrive_synced"): return
    ds=gdrive.status()
    if not ds.connected: return
    st.session_state["_gdrive_synced"]=True
    try:
        if gdrive.download_latest_history(config.HISTORY_FILE):
            history.clear(); st.session_state["_gdrive_msg"]="Google Driveから最新履歴を取得しました。"
        else:
            st.session_state["_gdrive_msg"]="Driveに履歴がないため同梱seedを使用します。"
    except Exception as e:
        st.session_state["_gdrive_msg"]=f"Drive履歴取得失敗: {e}"

handle_gdrive_oauth_callback()
sync_history_from_drive_once()

st.image(config.HEADER_IMAGE,use_container_width=True)
st.caption("Runaway's Race Development｜隊列・展開・Monte Carlo Simulation")
st.caption("Runaway's判定表=出馬表入力。Runaway's評価ロジックとSimulatorは独立。")
t1,t2,t3=st.tabs(["🎯 レース予測","🔄 TARGET年度更新","🧱 マスタ状態"])

with t2:
    up=st.file_uploader("TARGET年度馬単位CSV",type=["csv"],key="annual")
    if up:
        raw=read_csv_auto(up); st.info(f"{len(raw):,}行を読込")
        if st.button("差分確認",type="primary"):
            upd,a=upsert_annual(history(),raw); st.session_state["upd"]=upd; st.session_state["audit"]=a
        if "audit" in st.session_state:
            a=st.session_state["audit"]; c=st.columns(4)
            for col,k in zip(c,["INSERT","UPDATE","SKIP","更新後件数"]): col.metric(k,f"{a[k]:,}")
            if st.button("履歴マスタへ反映"):
                ds=gdrive.status()
                if ds.connected:
                    try:
                        gdrive.backup_current_history(config.HISTORY_FILE)
                    except Exception as e:
                        st.warning(f"Driveバックアップ失敗: {e}")
                save_history(st.session_state["upd"],config.HISTORY_FILE)
                history.clear()
                if ds.connected:
                    try:
                        fid=gdrive.upload_latest_history(config.HISTORY_FILE)
                        audit=dict(st.session_state.get("audit",{})); audit["timestamp"]=pd.Timestamp.now().isoformat(); audit["history_file_id"]=fid
                        gdrive.append_update_log(audit,"data/update_log_tmp.csv")
                        st.success("更新完了。Google Driveへ最新履歴を保存しました。")
                    except Exception as e:
                        st.error(f"ローカル更新は完了しましたがDrive保存に失敗: {e}")
                else:
                    st.success("更新完了（ローカル保存）")

with t3:

    st.subheader("Google Drive OAuth")
    ds=gdrive.status()
    if ds.connected:
        st.success("Google Drive OAuth接続済み")
        st.caption(f"folder_id: {ds.folder_id}")
        c1,c2=st.columns(2)
        if c1.button("Driveから最新履歴を再取得"):
            try:
                if gdrive.download_latest_history(config.HISTORY_FILE):
                    history.clear(); st.success("最新履歴を取得しました。")
                else: st.info("Driveにhistory_master.csv.gzがまだありません。")
            except Exception as e: st.error(f"取得失敗: {e}")
        if c2.button("Drive接続を解除"):
            gdrive.disconnect(); st.session_state.pop("_gdrive_synced",None); st.rerun()
    elif gdrive.enabled and gdrive.configured():
        st.info("Google Driveへの接続が必要です。")
        st.link_button("Google Driveに接続",gdrive.authorization_url())
    elif gdrive.enabled:
        st.warning("OAuth設定が未完了です。Streamlit Secretsを設定してください。")
    else:
        st.info("Google Drive連携OFF。ローカル履歴を使用中。")
    if st.session_state.get("_gdrive_msg"): st.caption(st.session_state["_gdrive_msg"])

    h=history(); st.metric("履歴行数",f"{len(h):,}")
    if len(h): st.write(f"期間 {int(pd.to_numeric(h['date'],errors='coerce').min())} ～ {int(pd.to_numeric(h['date'],errors='coerce').max())}")

with t1:
    up=st.file_uploader("Runaway's判定表（Excel/CSV）",type=["xlsx","xlsm","csv"],key="run")
    if not up: st.info("判定表を投入してください。"); st.stop()
    table,sheet=read_runaway_file(up); st.caption(f"出馬表として使用: {sheet}")
    dates=sorted(pd.to_numeric(table["年月日"],errors="coerce").dropna().astype(int).unique()) if "年月日" in table.columns else []
    d=st.selectbox("日付",dates,index=len(dates)-1) if dates else None; x=table.copy()
    if d is not None: x=x[pd.to_numeric(x["年月日"],errors="coerce")==d]
    pl=st.selectbox("開催場",sorted(x["場所"].dropna().astype(str).unique())); x=x[x["場所"].astype(str)==pl]
    rr=st.selectbox("R",sorted(pd.to_numeric(x["R"],errors="coerce").dropna().astype(int).unique())); e=x[pd.to_numeric(x["R"],errors="coerce")==rr].copy()
    surface=str(e["芝・ダ"].iloc[0]); dist=float(pd.to_numeric(e["距離"],errors="coerce").iloc[0]); year=int(str(d)[:4]) if d else pd.Timestamp.today().year

    feat=build_features(e,history(),course_row(pl,surface,dist))
    pred,ri=predict(feat)
    pred=assign_grade(pred,thresholds(),year,surface)
    scen,pred=predict_scenario(pred,ri)

    c=st.columns(4)
    c[0].metric("先行圧力",ri["先行圧力"]); c[1].metric("LeadCompetition",f"{ri['LeadCompetitionIndex_v2']:.3f}")
    c[2].metric("逃げ密度",f"{ri['LeadDensity']:.3f}"); c[3].metric("先行密度",f"{ri['FrontDensity']:.3f}")

    st.subheader("レースシナリオ")
    s1,s2,s3,s4,s5=st.columns(5)
    s1.metric("SLOW",f"{scen['P_SLOW']*100:.1f}%"); s2.metric("EVEN",f"{scen['P_EVEN']*100:.1f}%")
    s3.metric("HIGH",f"{scen['P_HIGH']*100:.1f}%"); s4.metric("SPRINT",f"{scen['P_SPRINT_FINISH']*100:.1f}%")
    s5.metric("LONG",f"{scen['P_LONG_SPURT']*100:.1f}%")
    st.info(f"AUTO予測: {scen['PredictedScenario']} / confidence {scen['TopProbability']*100:.1f}%")
    mode=st.selectbox("シナリオ",["AUTO","SLOW","EVEN","HIGH","SPRINT_FINISH","LONG_SPURT"],key="scenario_mode")
    active=scen["PredictedScenario"] if mode=="AUTO" else mode
    pred=scenario_adjustment(pred,active)
    pred=add_movement_columns(pred)

    st.subheader("馬群図")
    st.markdown(render_flow(pred,active,ri),unsafe_allow_html=True)

    cols=[z for z in ["馬番","馬名","騎手","今回想定脚質","PredFirstRank","Pred3Rank","Pred4Rank","Pred4ScenarioRank","LeadProb_Jockey","JockeyLift4","FullWinProb","ScenarioFullWinProb","展開評価","展開評価ステータス","最終スコア_Ver7_1","最終評価_Ver7_1","調教本命"] if z in pred.columns]
    st.subheader("予測隊列"); st.dataframe(pred[cols].sort_values("Pred4ScenarioRank"),use_container_width=True,hide_index=True)
    q=pred.sort_values("Pred4ScenarioRank"); st.subheader("4角想定隊列"); st.write(" → ".join([f"{int(r['馬番'])} {r['馬名']}({r['今回想定脚質']})" for _,r in q.iterrows()]))

    st.subheader("🎲 Monte Carlo Simulation")
    mc1,mc2=st.columns([1,1])
    n_sims=mc1.selectbox("シミュレーション回数",[1000,5000,10000],index=0)
    mc_mode=mc2.selectbox("Monte Carloのシナリオ",["AUTO","SLOW","EVEN","HIGH","SPRINT_FINISH","LONG_SPURT"],index=0,
                          help="AUTOは5分類シナリオ確率から各試行ごとに抽選。手動は全試行を固定。")
    with st.spinner(f"{n_sims:,}回シミュレート中..."):
        mc,mcmeta=simulate_race(pred,scen,n_sims=n_sims,mode=mc_mode,seed=5601)
    mc_show=mc.copy()
    pct_cols=["MC勝率","MC連対率","MC複勝率","MC逃げ率","MC4角3番手内率","MC勝率95%下限","MC勝率95%上限"]
    for z in pct_cols:
        if z in mc_show.columns: mc_show[z]=(mc_show[z]*100).round(1)
    st.dataframe(mc_show[[c for c in ["馬番","馬名","今回想定脚質","展開評価","MC勝率","MC連対率","MC複勝率","MC4角3番手内率","MC逃げ率","MC平均着順","MC平均4角順位","MC勝率95%下限","MC勝率95%上限"] if c in mc_show.columns]],use_container_width=True,hide_index=True)
    topmc=mc.iloc[0]
    st.caption(f"MC勝率1位: {topmc['馬名']} {topmc['MC勝率']*100:.1f}% / {n_sims:,}回。勝率合計={mcmeta['win_rate_sum']*100:.1f}%")
    st.caption("MC勝率はSimulator内部モデルとレース内不確実性から得たシミュレーション推定値です。市場オッズやRunaway'sスコアは入力していません。")

    st.subheader("シナリオ別勝率")
    sc_cols=["馬番","馬名"]+[f"{s}_勝率" for s in ["SLOW","EVEN","HIGH","SPRINT_FINISH","LONG_SPURT"]]
    sc_show=mc[sc_cols].copy()
    for z in sc_cols[2:]: sc_show[z]=(sc_show[z]*100).round(1)
    st.dataframe(sc_show,use_container_width=True,hide_index=True)


    st.subheader("動き予測")
    st.caption("初角→3角→4角で、どの馬がどこで位置を上げる／下げる予測なのかを表示します。")
    st.markdown(render_movement_flow(pred),unsafe_allow_html=True)
    with st.expander("動き予測を表で確認"):
        st.dataframe(render_movement_table(pred),use_container_width=True,hide_index=True)

    st.subheader("位置関係の参考")
    top=pred.sort_values("FullWinProb",ascending=False).head(min(4,len(pred))); notes=[]
    for i in range(len(top)):
        for j in range(i+1,len(top)):
            a,b=top.iloc[i],top.iloc[j]
            notes.append({"組合せ":f"{a['馬名']} × {b['馬名']}","想定脚質":f"{a['今回想定脚質']} × {b['今回想定脚質']}","参考":note(a["今回想定脚質"],b["今回想定脚質"],ri["先行圧力"],pairref())})
    st.dataframe(pd.DataFrame(notes),use_container_width=True,hide_index=True)
    st.success("Race Development Engine: 正式隊列モデル + 5分類シナリオ + Monte Carlo Simulation。")
    st.caption("Runaway's最終スコアはSimulator予測入力には使用していません。")
