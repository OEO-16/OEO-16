import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# ==========================================
# 1. 数据库逻辑层 (保持绝对的健壮性)
# ==========================================

DB_NAME = 'rentals_pro_final.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS room_templates 
                 (room_id TEXT PRIMARY KEY, 
                  user_name TEXT,
                  std_rent REAL, std_net REAL, std_san REAL, std_mgmt REAL, std_oth REAL, 
                  std_water_u REAL, std_elec_u REAL, std_issuer TEXT, std_receiver TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bills 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  room_id TEXT, date TEXT, 
                  water_curr REAL, water_prev REAL, water_unit REAL,
                  elec_curr REAL, elec_prev REAL, elec_unit REAL,
                  rent_amt REAL, net_amt REAL, san_amt REAL, mgmt_amt REAL, other_amt REAL,
                  total_amt REAL)''')
    conn.commit()
    conn.close()

def get_room_template(room_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM room_templates WHERE room_id=?", (room_id,))
    res = c.fetchone()
    conn.close()
    if res:
        return {
            "user_name": str(res[1]) if res[1] else "",
            "rent": float(res[2] or 0.0), "net": float(res[3] or 0.0), 
            "san": float(res[4] or 0.0), "mgmt": float(res[5] or 0.0), 
            "oth": float(res[6] or 0.0), "w_u": float(res[7] or 0.0), 
            "e_u": float(res[8] or 0.0), "issuer": str(res[9]) if res[9] else "", 
            "receiver": str(res[10]) if res[10] else ""
        }
    return None

def save_template(room_id, user_name, rent, net, san, mgmt, oth, w_u, e_u, issuer, receiver):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    sql = "INSERT OR REPLACE INTO room_templates VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    vals = (str(room_id), str(user_name), float(rent), float(net), float(san), float(mgmt), float(oth), float(w_u), float(e_u), str(issuer), str(receiver))
    c.execute(sql, vals)
    conn.commit()
    conn.close()

def save_bill_transaction(room_id, date_str, w_c, w_p, w_u, e_c, e_p, e_u, rent, net, san, mgmt, oth, total):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    sql = "INSERT INTO bills (room_id, date, water_curr, water_prev, water_unit, elec_curr, elec_prev, elec_unit, rent_amt, net_amt, san_amt, mgmt_amt, other_amt, total_amt) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    vals = (str(room_id), str(date_str), float(w_c), float(w_p), float(w_u), float(e_c), float(e_p), float(e_u), float(rent), float(net), float(san), float(mgmt), float(oth), float(total))
    c.execute(sql, vals)
    conn.commit()
    conn.close()

def get_all_room_ids():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT room_id FROM room_templates", conn)
    conn.close()
    return df['room_id'].tolist()

def get_room_history(room_id):
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT date, water_curr, water_prev, water_unit, elec_curr, elec_prev, elec_unit, rent_amt, net_amt, san_amt, mgmt_amt, other_amt, total_amt FROM bills WHERE room_id='{room_id}' ORDER BY date DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_last_reading(room_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT water_curr, elec_curr FROM bills WHERE room_id=? ORDER BY date DESC LIMIT 1", (room_id,))
    res = c.fetchone()
    conn.close()
    return res if res else (0.0, 0.0)

# --- 初始化 ---
init_db()

# ==========================================
# 2. Streamlit UI 界面层
# ==========================================

st.set_page_config(page_title="公寓管家 Pro", layout="wide")

st.markdown("""
<style>
    .receipt-card { background-color: white; padding: 25px; border: 2px solid #000; color: black; font-family: serif; margin-bottom: 20px;}
    .receipt-table { width: 100%; border-collapse: collapse; background-color: white; color: black;}
    .receipt-table th, .receipt-table td { border: 1px solid black; padding: 8px; text-align: center; color: black;}
    .receipt-table th { background-color: #eee; }
    .text-right { text-align: right; }
    .total-row { font-weight: bold; font-size: 1.2em; background-color: #f9f9f9; }
</style>
""", unsafe_allow_html=True)

st.title("🏠 公寓房租管理系统 (Pro版)")

# --- 侧边栏 ---
st.sidebar.header("📂 房间管理")
all_rooms = get_all_room_ids()
selected_room = st.sidebar.selectbox("👈 第一步：选择当前房间", ["--- 请选择 ---"] + all_rooms)

# 新增房间
with st.sidebar.expander("➕ 新增/初始化房间"):
    with st.form("new_room_form"):
        nr_id = st.text_input("新房间号 (如: 101)")
        nr_name = st.text_input("初始住户姓名")
        if st.form_submit_button("立即创建并初始化"):
            if nr_id and nr_name:
                save_template(nr_id, nr_name, 1000.0, 0.0, 0.0, 0.0, 0.0, 3.5, 1.2, "管理员", "管理员")
                st.success(f"房间 {nr_id} 已创建")
                st.rerun()
            else:
                st.error("请填写房号和姓名")

if selected_room != "--- 请选择 ---":
    template = get_room_template(selected_room)
    if not template:
        template = {"user_name": "未知", "rent": 0.0, "net": 0.0, "san": 0.0, "mgmt": 0.0, "oth": 0.0, "w_u": 0.0, "e_u": 0.0, "issuer": "", "receiver": ""}

    tab_input, tab_setup, tab_history = st.tabs(["✍️ 录入/预览", "⚙️ 房间配置", "📜 历史记录"])

    # --- TAB 1: 录入/预览 ---
    with tab_input:
        last_w, last_e = get_last_reading(selected_room)
        col_in, col_pre = st.columns([1, 1])

        with col_in:
            st.subheader(f"📝 录入: {selected_room}")
            with st.expander("👤 基础信息 (此月临时修改)", expanded=True):
                input_user = st.text_input("当前住户", value=template['user_name'])
                bill_date = st.date_input("账单日期", value=date.today())
                input_issuer = st.text_input("开票人", value=template['issuer'])
                input_receiver = st.text_input("收款人", value=template['receiver'])

            with st.expander("💧 水电读数", expanded=True):
                w_c = st.number_input("水费-本月读数", value=float(last_w), format="%.1f")
                w_p = st.number_input("水费-上月读数", value=float(last_w), format="%.1f")
                w_u = st.number_input("水费-单价", value=float(template['w_u']), step=0.1, format="%.2f")
                st.divider()
                e_c = st.number_input("电费-本月读数", value=float(last_e), format="%.1f")
                e_p = st.number_input("电费-上月读数", value=float(last_e), format="%.1f")
                e_u = st.number_input("电费-单价", value=float(template['e_u']), step=0.1, format="%.2f")

            with st.expander("💰 固定金额 (此月临时修改)", expanded=True):
                rent = st.number_input("房租", value=float(template['rent']), step=1.0)
                net = st.number_input("网费", value=float(template['net']), step=1.0)
                san = st.number_input("卫生费", value=float(template['san']), step=1.0)
                mgmt = st.number_input("管理费", value=float(template['mgmt']), step=1.0)
                oth = st.number_input("其它", value=float(template['oth']), step=1.0)

            # 计算逻辑
            w_usage = w_c - w_p
            e_usage = e_c - e_p
            w_amt = w_usage * w_u
            e_amt = e_usage * e_u
            grand_total = rent + w_amt + e_amt + net + san + mgmt + oth

            if st.button("💾 确认并保存本月账单", use_container_width=True, type="primary"):
                if w_usage < 0 or e_usage < 0:
                    st.error("错误：本月读数不能小于上月读数！")
                else:
                    save_bill_transaction(selected_room, str(bill_date), w_c, w_p, w_u, e_c, e_p, e_u, rent, net, san, mgmt, oth, grand_total)
                    st.success("✅ 存档成功！")
                    st.rerun()

        with col_pre:
            st.subheader("🖼️ 收据实时预览")
            # 【核心修正】：在 HTML 中分别使用三个不同的变量
            html_rec = f"""
            <div class="receipt-card">
                <h2 style="text-align:center;">房租 水费 电费 （专用）收据</h2>
                <p>用户名：({input_user}) {selected_room}房 &nbsp;&nbsp;&nbsp;&nbsp; 日期：{bill_date.strftime('%Y年%m月%d日')}</p>
                <table class="receipt-table">
                    <tr><th style="width:25%">项目</th><th style="width:15%">本月</th><th style="width:15%">上月</th><th style="width:15%">单价</th><th style="width:15%">实用</th><th style="width:15%">金额</th></tr>
                    <tr><td class="text-left">水费(方)</td><td>{w_c:.1f}</td><td>{w_p:.1f}</td><td>{w_u:.2f}</td><td>{w_usage:.1f}</td><td class="text-right">{w_amt:.2f}</td></tr>
                    <tr><td class="text-left">电费(度)</td><td>{e_c:.1f}</td><td>{e_p:.1f}</td><td>{e_u:.2f}</td><td>{e_usage:.1f}</td><td class="text-right">{e_amt:.2f}</td></tr>
                    <tr><td class="text-left">房租</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="text-right">{rent:.2f}</td></tr>
                    <tr><td class="text-left">网费</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="text-right">{net:.2f}</td></tr>
                    <tr><td class="text-left">卫生费</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="text-right">{san:.2f}</td></tr>
                    <tr><td class="text-left">管理费</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="text-right">{mgmt:.2f}</td></tr>
                    <tr><td class="text-left">其它</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="text-right">{oth:.2f}</td></tr>
                    <tr class="total-row"><td colspan="5" class="text-right">合计金额 (人民币):</td><td class="text-right">¥{grand_total:,.2f}</td></tr>
                </table>
                <div style="display:flex; justify-content:space-between; margin-top:40px; font-weight:bold;">
                    <span>开票人: {input_issuer}</span>
                    <span>收款人: {input_receiver}</span>
                </div>
            </div>
            """
            st.markdown(html_rec, unsafe_allow_html=True)

    # --- TAB 2: 房间配置 ---
    with tab_setup:
        st.subheader("⚙️ 房间配置 (设定默认值)")
        st.info("此处修改的值将成为该房间下个月录入时的‘默认初值’。")
        with st.form("setup_form"):
            s_user = st.text_input("默认住户姓名", value=template['user_name'])
            s_rent = st.number_input("默认房租", value=float(template['rent']))
            s_net = st.number_input("默认网费", value=float(template['net']))
            s_san = st.number_input("默认卫生费", value=float(template['san']))
            s_mgmt = st.number_input("默认管理费", value=float(template['mgmt']))
            s_oth = st.number_input("默认其它", value=float(template['oth']))
            s_wu = st.number_input("默认水费单价", value=float(template['w_u']), step=0.01)
            s_eu = st.number_input("默认电费单价", value=float(template['e_u']), step=0.01)
            s_issuer = st.text_input("默认开票人", value=template['issuer'])
            s_receiver = st.text_input("默认收款人", value=template['receiver'])
            if st.form_submit_button("💾 更新该房配置"):
                save_template(selected_room, s_user, s_rent, s_net, san, mgmt, oth, s_wu, s_eu, s_issuer, s_receiver)
                st.success("配置已更新！")
                st.rerun()

    # --- TAB 3: 历史记录 ---
    with tab_history:
        st.subheader(f"📜 {selected_room} 历史账单")
        history_df = get_room_history(selected_room)
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("暂无历史记录")

else:
    st.info("👈 请从左侧菜单选择一个房间，或者使用“新增房间”功能。")
