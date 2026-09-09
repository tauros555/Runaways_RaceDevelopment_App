import pandas as pd
import streamlit as st
import config

from modules.gdrive_oauth_storage import GoogleDriveOAuthStorage
from modules.history_store import read_csv_auto, load_history, upsert_annual, save_history
from modules.feature_engine import build_features
from modules.simulator_engine import predict, assign_grade
from modules.pair_reference import note
from modules.scenario_engine import predict_scenario, scenario_adjustment
from modules.queue_visual import render_flow
from modules.monte_carlo import simulate_race
from modules.movement_visual import add_movement_columns, render_movement_table, render_movement_flow
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
    c = course()
    surf = "芝" if surface == "芝" else "ダート"
    z = c[
        (c["場所"].astype(str) == str(place))
        & (c["芝・ダート"].astype(str) == surf)
        & (pd.to_numeric(c["距離"], errors="coerce") == float(distance))
    ]
    return z.iloc[0].to_dict() if len(z) else {}

gdrive = GoogleDriveOAuthStorage(st.secrets, st.session_state)

def handle_gdrive_oauth_callback():
    try:
        code = st.query_params.get("code")
        if isinstance(code, list):
            code = code[0] if code else None
        if code and not st.session_state.get("_gdrive_oauth_code_done"):
            gdrive.exchange_code(code)
            st.session_state["_gdrive_oauth_code_done"] = True
            st.session_state["_gdrive_msg"] = "Google Drive認証が完了しました。"
            try:
                st.query_params.clear()
            except Exception:
                pass
    except Exception as e:
        st.session_state["_gdrive_msg"] = f"OAuth認証処理失敗: {e}"

def sync_history_from_drive_once():
    if st.session_state.get("_gdrive_synced"):
        return
    ds = gdrive.status()
    if not ds.connected:
        return
    try:
        if gdrive.download_latest_history(config.HISTORY_FILE):
            history.clear()
            st.session_state["_gdrive_msg"] = "Google Driveから最新履歴を取得しました。"
        else:
            st.session_state["_gdrive_msg"] = "Driveに履歴がないため同梱seedを使用します。"
        st.session_state["_gdrive_synced"] = True
    except Exception as e:
        st.session_state["_gdrive_msg"] = f"Drive履歴取得失敗: {e}"

handle_gdrive_oauth_callback()
sync_history_from_drive_once()

# Header
st.image(config.HEADER_IMAGE, use_container_width=True)

# Navigation - IMPORTANT: unlike st.tabs, only the selected page executes.
page = st.sidebar.radio(
    "Race Development",
    ["🎯 レース予測", "🔄 TARGET年度更新", "☁ Google Drive", "🧱 マスタ状態"],
    index=0,
)

st.sidebar.caption("v6.6 CLOUD FIX")
st.sidebar.caption("出馬表: data/調教判定表.csv")

# --------------------
# Google Drive page
# --------------------
if page == "☁ Google Drive":
    st.header("Google Drive OAuth")
    ds = gdrive.status()

    if ds.connected:
        st.success("Google Drive OAuth接続済み")
        st.caption(f"folder_id: {ds.folder_id}")

        c1, c2 = st.columns(2)
        if c1.button("Driveから最新履歴を再取得", type="primary"):
            try:
                if gdrive.download_latest_history(config.HISTORY_FILE):
                    history.clear()
                    st.success("最新履歴を取得しました。")
                else:
                    st.info("Driveにhistory_master.csv.gzがまだありません。")
            except Exception as e:
                st.error(f"取得失敗: {e}")

        if c2.button("Drive接続を解除"):
            gdrive.disconnect()
            st.session_state.pop("_gdrive_synced", None)
            st.rerun()

    elif gdrive.enabled and gdrive.configured():
        st.info("Google Driveへの接続が必要です。")
        st.link_button("Google Driveに接続", gdrive.authorization_url(), type="primary")
        st.caption("Googleの認証画面で、ご自身のGoogleアカウントを選択してください。")

    elif gdrive.enabled:
        st.warning("OAuth設定が未完了です。Streamlit CloudのSecretsを設定してください。")
        st.code(
            """[gdrive_oauth]
enabled = true
client_id = "..."
client_secret = "..."
redirect_uri = "https://あなたのアプリ.streamlit.app"
folder_id = "..."
history_filename = "history_master.csv.gz"
backup_folder_name = "backup"
log_filename = "update_log.csv" """,
            language="toml",
        )
    else:
        st.info("Google Drive連携は現在OFFです。")
        st.write("Streamlit Cloud → App settings → Secrets に gdrive_oauth 設定を入れると接続ボタンが有効になります。")

    if st.session_state.get("_gdrive_msg"):
        st.caption(st.session_state["_gdrive_msg"])
    st.stop()

# --------------------
# Master status page
# --------------------
if page == "🧱 マスタ状態":
    st.header("マスタ状態")

    h = history()
    c1, c2, c3 = st.columns(3)
    c1.metric("履歴行数", f"{len(h):,}")

    if len(h):
        d = pd.to_numeric(h["date"], errors="coerce").dropna()
        if len(d):
            c2.metric("開始", str(int(d.min())))
            c3.metric("最新", str(int(d.max())))

    try:
        rc = racecard_master()
        st.success(f"data/調教判定表.csv 読込OK：{len(rc):,}行")
        races = available_races(rc)
        st.write(f"登録レース数: {len(races):,}")
        st.dataframe(races.head(30), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"調教判定表読込失敗: {e}")
    st.stop()

# --------------------
# TARGET update page
# --------------------
if page == "🔄 TARGET年度更新":
    st.header("TARGET年度更新")
    up = st.file_uploader("TARGET年度馬単位CSV", type=["csv"], key="annual")

    if up:
        raw = read_csv_auto(up)
        st.info(f"{len(raw):,}行を読込")

        if st.button("差分確認", type="primary"):
            upd, a = upsert_annual(history(), raw)
            st.session_state["upd"] = upd
            st.session_state["audit"] = a

        if "audit" in st.session_state:
            a = st.session_state["audit"]
            cols = st.columns(4)
            for col, k in zip(cols, ["INSERT", "UPDATE", "SKIP", "更新後件数"]):
                col.metric(k, f"{a[k]:,}")

            if st.button("履歴マスタへ反映"):
                ds = gdrive.status()

                if ds.connected:
                    try:
                        gdrive.backup_current_history(config.HISTORY_FILE)
                    except Exception as e:
                        st.warning(f"Driveバックアップ失敗: {e}")

                save_history(st.session_state["upd"], config.HISTORY_FILE)
                history.clear()

                if ds.connected:
                    try:
                        fid = gdrive.upload_latest_history(config.HISTORY_FILE)
                        audit = dict(st.session_state.get("audit", {}))
                        audit["timestamp"] = pd.Timestamp.now().isoformat()
                        audit["history_file_id"] = fid
                        gdrive.append_update_log(audit, "data/update_log_tmp.csv")
                        st.success("更新完了。Google Driveへ最新履歴を保存しました。")
                    except Exception as e:
                        st.error(f"ローカル更新は完了しましたがDrive保存に失敗: {e}")
                else:
                    st.success("更新完了（ローカル保存）")
    st.stop()

# --------------------
# Race prediction page
# --------------------
st.header("Race Development")

try:
    rc = racecard_master()
except Exception as e:
    st.error(f"data/調教判定表.csv を読み込めません: {e}")
    st.stop()

races = available_races(rc)
if races.empty:
    st.warning("調教判定表にレースがありません。")
    st.stop()

# Three-step selector from the local data file, no browser upload.
dates = sorted(pd.to_numeric(races["年月日"], errors="coerce").dropna().astype(int).unique(), reverse=True)
sel_date = st.selectbox("日付", dates, index=0)
r1 = races[pd.to_numeric(races["年月日"], errors="coerce") == sel_date]

places = sorted(r1["場所"].dropna().astype(str).unique())
sel_place = st.selectbox("開催場", places)
r2 = r1[r1["場所"].astype(str) == sel_place]

rs = sorted(pd.to_numeric(r2["R"], errors="coerce").dropna().astype(int).unique())
sel_r = st.selectbox("R", rs)

rr = r2[pd.to_numeric(r2["R"], errors="coerce") == sel_r].iloc[0]
current = select_race(rc, rr["current_race_key"])
current = add_attention_flags(current)

surface = str(current["芝・ダ"].iloc[0])
dist = float(pd.to_numeric(current["距離"], errors="coerce").iloc[0])
year = int(str(sel_date)[:4])

st.caption(
    f"参照元: data/調教判定表.csv ｜ "
    f"{sel_date} {sel_place} {sel_r}R {rr['レース名']} {surface}{int(dist)}m ｜ "
    f"{len(current)}頭"
)

# Attention badges from training judgment table.
att = attention_summary(current)
if not att.empty:
    st.subheader("調教判定表 注目馬")
    cols = st.columns(min(3, len(att)))
    for i, (_, r) in enumerate(att.iterrows()):
        with cols[i % len(cols)]:
            st.info(f"{int(r['馬番'])} {r['馬名']}\n\n{r['注目フラグ']}")

# Prediction model execution with a clear deployment-compatibility message.
try:
    feat = build_features(current, history(), course_row(sel_place, surface, dist))
    pred, ri = predict(feat)
except ModuleNotFoundError as e:
    st.error("学習済みモデルの実行環境が一致していません。")
    st.code(str(e))
    st.warning(
        "Streamlit Community Cloudを Python 3.13 で再デプロイしてください。"
        "このモデル群はPython 3.13 + scikit-learn 1.8系で動作確認しています。"
    )
    st.stop()
except Exception as e:
    st.error("隊列モデルの実行中にエラーが発生しました。")
    st.exception(e)
    st.stop()

pred = assign_grade(pred, thresholds(), year, surface)
scen, pred = predict_scenario(pred, ri)

m = st.columns(4)
m[0].metric("先行圧力", ri["先行圧力"])
m[1].metric("LeadCompetition", f"{ri['LeadCompetitionIndex_v2']:.3f}")
m[2].metric("逃げ密度", f"{ri['LeadDensity']:.3f}")
m[3].metric("先行密度", f"{ri['FrontDensity']:.3f}")

st.subheader("レースシナリオ")
ss = st.columns(5)
for col, label, key in zip(
    ss,
    ["SLOW", "EVEN", "HIGH", "SPRINT", "LONG"],
    ["P_SLOW", "P_EVEN", "P_HIGH", "P_SPRINT_FINISH", "P_LONG_SPURT"],
):
    col.metric(label, f"{scen[key] * 100:.1f}%")

st.info(f"AUTO予測: {scen['PredictedScenario']} / confidence {scen['TopProbability']*100:.1f}%")

mode = st.selectbox(
    "シナリオ",
    ["AUTO", "SLOW", "EVEN", "HIGH", "SPRINT_FINISH", "LONG_SPURT"],
)
active = scen["PredictedScenario"] if mode == "AUTO" else mode
pred = scenario_adjustment(pred, active)
pred = add_movement_columns(pred)

st.subheader("馬群図")
st.markdown(render_flow(pred, active, ri), unsafe_allow_html=True)

st.subheader("予測隊列")
cols = [
    z for z in [
        "馬番","馬名","騎手","今回想定脚質",
        "PredFirstRank","Pred3Rank","Pred4ScenarioRank",
        "LeadProb_Jockey","JockeyLift4","FullWinProb",
        "ScenarioFullWinProb","展開評価"
    ] if z in pred.columns
]
st.dataframe(
    pred[cols].sort_values("Pred4ScenarioRank"),
    use_container_width=True,
    hide_index=True,
)

st.subheader("動き予測")
st.markdown(render_movement_flow(pred), unsafe_allow_html=True)

st.subheader("Monte Carlo Simulation")
c1, c2 = st.columns(2)
n_sims = c1.selectbox("シミュレーション回数", [1000, 5000, 10000], index=0)
mc_mode = c2.selectbox(
    "Monte Carloシナリオ",
    ["AUTO", "SLOW", "EVEN", "HIGH", "SPRINT_FINISH", "LONG_SPURT"],
    index=0,
)

with st.spinner(f"{n_sims:,}回シミュレート中..."):
    mc, mcmeta = simulate_race(pred, scen, n_sims=n_sims, mode=mc_mode, seed=5601)

show = mc.copy()
for z in [
    "MC勝率","MC連対率","MC複勝率","MC逃げ率",
    "MC4角3番手内率","MC勝率95%下限","MC勝率95%上限"
]:
    if z in show.columns:
        show[z] = (show[z] * 100).round(1)

st.dataframe(
    show[[c for c in [
        "馬番","馬名","今回想定脚質","展開評価",
        "MC勝率","MC連対率","MC複勝率",
        "MC4角3番手内率","MC逃げ率",
        "MC平均着順","MC平均4角順位",
        "MC勝率95%下限","MC勝率95%上限"
    ] if c in show.columns]],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"勝率合計={mcmeta['win_rate_sum']*100:.1f}% ｜ "
    "市場オッズ・Runaway's最終スコアはSimulator入力に使用していません。"
)

st.subheader("シナリオ別勝率")
sc_cols = ["馬番","馬名"] + [f"{s}_勝率" for s in ["SLOW","EVEN","HIGH","SPRINT_FINISH","LONG_SPURT"]]
sc_show = mc[[c for c in sc_cols if c in mc.columns]].copy()
for z in sc_cols[2:]:
    if z in sc_show.columns:
        sc_show[z] = (sc_show[z] * 100).round(1)
st.dataframe(sc_show, use_container_width=True, hide_index=True)

st.subheader("位置関係の参考")
top = pred.sort_values("FullWinProb", ascending=False).head(min(4, len(pred)))
notes = []
for i in range(len(top)):
    for j in range(i+1, len(top)):
        a, b = top.iloc[i], top.iloc[j]
        notes.append({
            "組合せ": f"{a['馬名']} × {b['馬名']}",
            "想定脚質": f"{a['今回想定脚質']} × {b['今回想定脚質']}",
            "参考": note(a["今回想定脚質"], b["今回想定脚質"], ri["先行圧力"], pairref()),
        })
st.dataframe(pd.DataFrame(notes), use_container_width=True, hide_index=True)
