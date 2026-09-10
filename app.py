import pandas as pd
import streamlit as st
import config

from modules.gdrive_oauth_storage import GoogleDriveOAuthStorage
from modules.history_store import read_csv_auto, load_history, upsert_annual, save_history
from modules.feature_engine import build_features
from modules.simulator_engine import predict, assign_grade
from modules.pair_reference import note
from modules.scenario_engine import predict_scenario, scenario_adjustment
from modules.route_bias import resolve_auto_bias, assign_route_positions, render_route_grid
from modules.early_speed_view import render_ten_battle
from modules.monte_carlo import simulate_race
from modules.movement_visual import add_movement_columns, render_movement_table
from modules.racecard_local import load_training_judgment_racecard, available_races, select_race
from modules.attention_flags import add_attention_flags, attention_summary

st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data(show_spinner=False)
def course():
    return pd.read_csv(config.COURSE_FILE, encoding="cp932", low_memory=False)

@st.cache_data(show_spinner=False)
def thresholds():
    return pd.read_csv(config.THRESHOLD_FILE, encoding="cp932", low_memory=False)

@st.cache_data(show_spinner=False)
def pairref():
    return pd.read_csv(config.PAIR_REFERENCE_FILE, encoding="cp932", low_memory=False)

@st.cache_data(show_spinner="履歴マスタ読込中...")
def history():
    return load_history(config.HISTORY_FILE, config.SEED_HISTORY_FILE)

@st.cache_data(show_spinner=False)
def racecard_master():
    return load_training_judgment_racecard(config.RACECARD_FILE)

def course_row(place, surface, distance):
    c=course()
    surf="芝" if surface=="芝" else "ダート"
    z=c[
        (c["場所"].astype(str)==str(place))
        &(c["芝・ダート"].astype(str)==surf)
        &(pd.to_numeric(c["距離"],errors="coerce")==float(distance))
    ]
    return z.iloc[0].to_dict() if len(z) else {}

gdrive=GoogleDriveOAuthStorage(st.secrets,st.session_state)

def handle_oauth_callback():
    try:
        code=st.query_params.get("code")
        if isinstance(code,list):
            code=code[0] if code else None
        if code and not st.session_state.get("_oauth_done"):
            gdrive.exchange_code(code)
            st.session_state["_oauth_done"]=True
            st.session_state["_gdrive_msg"]="Google Drive認証が完了しました。"
            try: st.query_params.clear()
            except Exception: pass
    except Exception as e:
        st.session_state["_gdrive_msg"]=f"OAuth認証処理失敗: {e}"

handle_oauth_callback()

st.image(config.HEADER_IMAGE,use_container_width=True)

page=st.sidebar.radio(
    "Race Development",
    ["🎯 レース予測","☁ Google Drive","🧱 データ状態"],
    index=0,
)
st.sidebar.caption("v6.8 ROUTE BIAS")
st.sidebar.caption("出馬表：data/調教判定表.csv")

if page=="☁ Google Drive":
    st.header("Google Drive")
    ds=gdrive.status()
    if ds.connected:
        st.success("Google Drive OAuth接続済み")
        st.caption(f"folder_id: {ds.folder_id}")
        if st.button("Driveから最新履歴を取得",type="primary"):
            try:
                if gdrive.download_latest_history(config.HISTORY_FILE):
                    history.clear()
                    st.success("最新履歴を取得しました。")
                else:
                    st.info("Driveにhistory_master.csv.gzがありません。")
            except Exception as e:
                st.error(f"取得失敗: {e}")
        if st.button("接続解除"):
            gdrive.disconnect()
            st.rerun()
    elif gdrive.enabled and gdrive.configured():
        st.info("Google Driveへの接続が必要です。")
        st.link_button("Google Driveに接続",gdrive.authorization_url(),type="primary")
    elif gdrive.enabled:
        st.warning("OAuth設定が未完了です。Streamlit Secretsを設定してください。")
    else:
        st.info("Google Drive連携OFF。")
    if st.session_state.get("_gdrive_msg"):
        st.caption(st.session_state["_gdrive_msg"])
    st.stop()

if page=="🧱 データ状態":
    st.header("データ状態")
    try:
        rc=racecard_master()
        races=available_races(rc)
        invalid=(~rc["_date_valid"]).sum() if "_date_valid" in rc.columns else 0
        c1,c2,c3=st.columns(3)
        c1.metric("調教判定表 行数",f"{len(rc):,}")
        c2.metric("有効レース",f"{len(races):,}")
        c3.metric("除外した不正日付行",f"{int(invalid):,}")
        st.dataframe(races.head(50),use_container_width=True,hide_index=True)
    except Exception as e:
        st.error(e)
    st.info("履歴マスタはこのページでは自動読込しません。重い処理はレース予測実行時だけ行います。")
    st.stop()

# Race prediction page
st.header("Race Development")

try:
    rc=racecard_master()
    races=available_races(rc)
except Exception as e:
    st.error(f"data/調教判定表.csv 読込失敗: {e}")
    st.stop()

if races.empty:
    st.warning("有効なレース日付がありません。YYYYMMDDの8桁日付のみ利用します。")
    st.stop()

# Strict date selector
date_rows=races[["年月日","日付表示"]].drop_duplicates().sort_values("年月日",ascending=False)
date_map={r["日付表示"]:int(r["年月日"]) for _,r in date_rows.iterrows()}
date_label=st.selectbox("日付",list(date_map.keys()))
sel_date=date_map[date_label]

r1=races[races["年月日"]==sel_date]
places=sorted(r1["場所"].dropna().astype(str).unique())
sel_place=st.selectbox("開催場",places)

r2=r1[r1["場所"].astype(str)==sel_place]
rs=sorted(pd.to_numeric(r2["R"],errors="coerce").dropna().astype(int).unique())
sel_r=st.selectbox("R",rs)

rr=r2[pd.to_numeric(r2["R"],errors="coerce")==sel_r].iloc[0]
current=select_race(rc,rr["current_race_key"])
current=add_attention_flags(current)

surface=str(current["芝・ダ"].iloc[0])
dist=float(pd.to_numeric(current["距離"],errors="coerce").iloc[0])
year=int(str(sel_date)[:4])
race_key=str(rr["current_race_key"])

st.caption(
    f"参照元：data/調教判定表.csv ｜ {date_label} {sel_place} {sel_r}R "
    f"{rr['レース名']} {surface}{int(dist)}m ｜ {len(current)}頭"
)


# 馬場状態はユーザー観察値。進路バイアスはAUTOまたは手動指定。
st.subheader("馬場・進路バイアス")
bc1,bc2=st.columns(2)
going=bc1.selectbox("馬場状態",["未指定","良","稍重","重","不良"],index=0)
bias_mode=bc2.selectbox(
    "進路有利想定",
    ["AUTO","内有利","やや内有利","フラット","やや外有利","外有利"],
    index=0,
)
cr=course_row(sel_place,surface,dist)
auto_bias,auto_reason=resolve_auto_bias(cr)
effective_bias=auto_bias if bias_mode=="AUTO" else bias_mode
st.info(f"適用バイアス：**{effective_bias}**　｜　馬場状態：{going}")
if bias_mode=="AUTO":
    st.caption(f"AUTO根拠：{auto_reason}")
else:
    st.caption("手動指定をAUTOより優先しています。馬場状態を見て当日の内外有利を変更できます。")

# Reset prior prediction if selection changed
if st.session_state.get("_active_race_key") not in (None,race_key):
    for k in ["_pred_result","_scenario","_raceinfo","_active_scenario","_mc_result","_mc_meta"]:
        st.session_state.pop(k,None)
st.session_state["_active_race_key"]=race_key

# Attention flags always visible without loading history/models
att=attention_summary(current)
if not att.empty:
    st.subheader("調教判定表 注目馬")
    cols=st.columns(min(3,max(1,len(att))))
    for i,(_,r) in enumerate(att.iterrows()):
        with cols[i%len(cols)]:
            st.info(f"{int(r['馬番'])} {r['馬名']}\n\n{r['注目フラグ']}")

st.divider()
st.subheader("予測実行")
st.caption("レース選択だけでは履歴マスタや学習済みモデルを読み込みません。下のボタンを押した時だけ計算します。")

if st.button("▶ Race Development予測を実行",type="primary",use_container_width=True):
    with st.spinner("履歴・モデルを読み込み、隊列とシナリオを計算しています..."):
        feat=build_features(current,history(),course_row(sel_place,surface,dist))
        pred,ri=predict(feat)
        pred=assign_grade(pred,thresholds(),year,surface)
        scen,pred=predict_scenario(pred,ri)
        active=scen["PredictedScenario"]
        pred=scenario_adjustment(pred,active)
        pred=add_movement_columns(pred)
        st.session_state["_pred_result"]=pred
        st.session_state["_scenario"]=scen
        st.session_state["_raceinfo"]=ri
        st.session_state["_active_scenario"]=active
        st.session_state.pop("_mc_result",None)
        st.session_state.pop("_mc_meta",None)

if "_pred_result" not in st.session_state:
    st.stop()

pred=st.session_state["_pred_result"].copy()
scen=st.session_state["_scenario"]
ri=st.session_state["_raceinfo"]

m=st.columns(4)
m[0].metric("先行圧力",ri["先行圧力"])
m[1].metric("LeadCompetition",f"{ri['LeadCompetitionIndex_v2']:.3f}")
m[2].metric("逃げ密度",f"{ri['LeadDensity']:.3f}")
m[3].metric("先行密度",f"{ri['FrontDensity']:.3f}")

st.subheader("テン争い")
st.markdown(render_ten_battle(pred),unsafe_allow_html=True)

st.subheader("レースシナリオ")
ss=st.columns(5)
for col,label,key in zip(
    ss,
    ["SLOW","EVEN","HIGH","SPRINT","LONG"],
    ["P_SLOW","P_EVEN","P_HIGH","P_SPRINT_FINISH","P_LONG_SPURT"],
):
    col.metric(label,f"{scen[key]*100:.1f}%")
st.info(f"AUTO予測：{scen['PredictedScenario']} / confidence {scen['TopProbability']*100:.1f}%")

mode=st.selectbox(
    "表示シナリオ",
    ["AUTO","SLOW","EVEN","HIGH","SPRINT_FINISH","LONG_SPURT"],
    index=0,
)
active=scen["PredictedScenario"] if mode=="AUTO" else mode
pred_view=scenario_adjustment(pred,active)
pred_view=add_movement_columns(pred_view)

# 内・中・外の進路推定と馬場バイアス補正
pred_view=assign_route_positions(pred_view,cr,effective_bias)

st.subheader("予想隊列")
st.caption("画面表示は初角と最終コーナーの2場面。横＝前後位置、縦＝内・中・外です。")
st.markdown(render_route_grid(pred_view,"初角",effective_bias),unsafe_allow_html=True)
st.markdown(render_route_grid(pred_view,"最終",effective_bias),unsafe_allow_html=True)

st.subheader("進路バイアス影響")
route_cols=[c for c in [
    "馬番","馬名","初角ゾーン","初角進路","最終角ゾーン","最終角進路",
    "進路バイアス評価","進路バイアス補正","展開評価"
] if c in pred_view.columns]
route_show=pred_view[route_cols].sort_values("Pred4ScenarioRank" if "Pred4ScenarioRank" in pred_view.columns else "馬番").copy()
if "進路バイアス補正" in route_show.columns:
    route_show["進路バイアス補正"]=(route_show["進路バイアス補正"]*100).round(1).astype(str)+"pt"
st.dataframe(route_show,use_container_width=True,hide_index=True)

with st.expander("予測値の詳細"):
    cols=[c for c in [
        "馬番","馬名","騎手","今回想定脚質",
        "StartDashScore","EarlyTrackingScore","LeadProb_Jockey",
        "PredFirstRank","Pred3Rank","Pred4ScenarioRank",
        "FullWinProb","ScenarioFullWinProb","展開評価"
    ] if c in pred_view.columns]
    st.dataframe(pred_view[cols].sort_values("Pred4ScenarioRank"),use_container_width=True,hide_index=True)

st.divider()
st.subheader("Monte Carlo Simulation")
st.caption("Monte Carloは自動実行しません。必要な時だけ実行します。")
mc1,mc2=st.columns(2)
n_sims=mc1.selectbox("シミュレーション回数",[1000,5000,10000],index=0)
mc_mode=mc2.selectbox(
    "Monte Carloシナリオ",
    ["AUTO","SLOW","EVEN","HIGH","SPRINT_FINISH","LONG_SPURT"],
    index=0,
)

if st.button(f"🎲 {n_sims:,}回シミュレーションを実行",use_container_width=True):
    with st.spinner(f"{n_sims:,}回シミュレート中..."):
        mc,meta=simulate_race(pred_view,scen,n_sims=n_sims,mode=mc_mode,seed=5601)
        st.session_state["_mc_result"]=mc
        st.session_state["_mc_meta"]=meta

if "_mc_result" in st.session_state:
    mc=st.session_state["_mc_result"].copy()
    meta=st.session_state["_mc_meta"]
    show=mc.copy()
    for c in [
        "MC勝率","MC連対率","MC複勝率","MC逃げ率",
        "MC4角3番手内率","MC勝率95%下限","MC勝率95%上限"
    ]:
        if c in show.columns:
            show[c]=(show[c]*100).round(1)
    show_cols=[c for c in [
        "馬番","馬名","今回想定脚質","展開評価",
        "MC勝率","MC連対率","MC複勝率","MC4角3番手内率",
        "MC逃げ率","MC平均着順","MC平均4角順位",
        "MC勝率95%下限","MC勝率95%上限"
    ] if c in show.columns]
    st.dataframe(show[show_cols],use_container_width=True,hide_index=True)
    st.caption(
        f"勝率合計={meta['win_rate_sum']*100:.1f}% ｜ "
        "市場オッズ・Runaway's最終スコアはSimulator入力に使用していません。"
    )
