import urllib.parse
import pandas as pd
import plotly.express as px
import streamlit as st

# ตั้งค่าหน้าเว็บแดชบอร์ด
st.set_page_config(
    page_title="Dashboard ยอดส่งระหว่างเดือน (Cross-Filter)",
    page_icon="📊",
    layout="wide",
)

# Custom CSS เพื่อตกแต่งโทนสีพาสเทล ฟ้า น้ำเงิน ขาว ให้ดูสบายตาและพรีเมียม
st.markdown(
    """
    <style>
    .main {
        background-color: #F4F7FC;
    }
    .stButton>button {
        background-color: #3B82F6;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2563EB;
        color: white;
    }
    div.stMetric {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #3B82F6;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📊 แดชบอร์ดวิเคราะห์ยอดส่งระหว่างเดือน (Multi-Dimensional Cross-Filter)")
st.markdown(
    "ระบบวิเคราะห์ข้อมูลเชื่อมต่อ Google Sheets แบบเรียลไทม์ ครอบคลุมทุกมิติ"
    " พร้อมระบบกรองข้อมูลข้ามกลุ่ม (Cross-Filtering)"
)

# 1. ฟังก์ชันโหลดข้อมูลแบบไม่จำกัดและรองรับอักขระพิเศษ
@st.cache_data(ttl=60)
def load_data():
  sheet_id = "1XRkHwEJoEPiVVortmkN60mN39TSsHN2JVo733US3fQs"
  sheet_name_encoded = urllib.parse.quote("ยอดส่งระหว่างเดือน")
  # ใช้ gviz แบบดึงข้อมูลดิบทั้งหมด เพื่อให้ครอบคลุมทุกแถวที่ซ่อนหรืออักขระพิเศษ
  url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"
  try:
    df = pd.read_csv(url)
    return df
  except Exception as e:
    # Fallback กรณีดึงแบบระบุชื่อชีทไม่ผ่าน ให้ดึงชีทแรกสุดแทน
    url_fallback = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url_fallback)
    return df


# โหลดข้อมูล
df_raw = load_data()

if df_raw.empty:
  st.error(
      "ไม่พบข้อมูลใน Google Sheets กรุณาตรวจสอบลิงก์หรือสิทธิ์การเข้าถึงอีกครั้ง"
  )
else:
  # ทำความสะอาดชื่อคอลัมน์
  df_raw.columns = df_raw.columns.str.strip()

  # จัดการ Session State สำหรับเก็บบันทึกการกรองข้ามกลุ่ม (Cross-Filter State)
  if "selected_filters" not in st.session_state:
    st.session_state.selected_filters = {}

  # Sidebar สำหรับควบคุมและรีเซ็ต
  st.sidebar.header("🎛️ ควบคุมแดชบอร์ด")
  if st.sidebar.button("🔄 รีเซ็ตตัวกรองทั้งหมด (Reset Filters)"):
    st.session_state.selected_filters = {}
    st.rerun()

  # คัดแยกประเภทคอลัมน์อัตโนมัติเพื่อใช้ทำมุมมองกราฟ
  cat_columns = [
      c
      for c in df_raw.columns
      if df_raw[c].dtype == "object" and len(df_raw[c].unique()) < 200
  ]
  num_columns = df_raw.select_dtypes(
      include=["float64", "int64"]
  ).columns.tolist()

  # กรองข้อมูลตามที่ผู้ใช้เลือกผ่าน Session State ข้ามกลุ่ม
  filtered_df = df_raw.copy()
  for col, val_list in st.session_state.selected_filters.items():
    if val_list and col in filtered_df.columns:
      filtered_df = filtered_df[filtered_df[col].isin(val_list)]

  # แสดงผล Metric ภาพรวม
  col_m1, col_m2, col_m3, col_m4 = st.columns(4)
  with col_m1:
    st.metric("📦 จำนวนรายการทั้งหมด", f"{len(filtered_df):,}")
  with col_m2:
    if num_columns:
      total_sum = filtered_df[num_columns[0]].sum()
      st.metric(f"💰 รวม {num_columns[0]}", f"{total_sum:,.2f}")
    else:
      st.metric("💰 ยอดรวม", "-")
  with col_m3:
    ratio_pct = (
        (len(filtered_df) / len(df_raw) * 100) if len(df_raw) > 0 else 0
    )
    st.metric("📈 สัดส่วนข้อมูลที่แสดง", f"{ratio_pct:.1f}%")
  with col_m4:
    st.metric(
        "🔗 เงื่อนไข Cross-Filter Active",
        f"{len(st.session_state.selected_filters)} มิติ",
    )

  st.markdown("---")

  # ตรวจสอบว่ามีคอลัมน์เพียงพอสำหรับสร้างกราฟ 3 มุมมองหรือไม่
  if len(cat_columns) >= 3:
    c1, c2, c3 = st.columns(3)

    pastel_colors = px.colors.qualitative.Pastel1

    # --- มุมมองที่ 1: กราฟวงกลม (Pie Chart) แสดงสัดส่วนเรื่องที่ 1 ---
    with c1:
      st.subheader(f"🌐 สัดส่วนตาม: {cat_columns[0]}")
      pie_data = (
          filtered_df[cat_columns[0]].value_counts().reset_index().head(8)
      )
      pie_data.columns = [cat_columns[0], "count"]

      fig_pie = px.pie(
          pie_data,
          names=cat_columns[0],
          values="count",
          hole=0.4,
          color_discrete_sequence=px.colors.sequential.Blues_r,
      )
      fig_pie.update_layout(
          margin=dict(t=20, b=20, l=20, r=20),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
      )

      # ใช้ st.plotly_chart พร้อมเปิด selection เพื่อให้คลิกกรองข้ามกลุ่มได้
      selected_pie = st.plotly_chart(
          fig_pie,
          use_container_width=True,
          key="pie_plot",
          on_select="rerun",
      )

      # จัดการ Event การคลิกที่กราฟวงกลม
      if (
          selected_pie
          and "selection" in selected_pie
          and selected_pie["selection"]["points"]
      ):
        selected_points = [
            p["label"] for p in selected_pie["selection"]["points"]
        ]
        st.session_state.selected_filters[cat_columns[0]] = selected_points
        st.rerun()

    # --- มุมมองที่ 2: กราฟแท่ง (Bar Chart) แสดงเปรียบเทียบเรื่องที่ 2 ---
    with c2:
      st.subheader(f"📊 เปรียบเทียบตาม: {cat_columns[1]}")
      bar_data = (
          filtered_df[cat_columns[1]].value_counts().reset_index().head(10)
      )
      bar_data.columns = [cat_columns[1], "count"]

      fig_bar = px.bar(
          bar_data,
          x=cat_columns[1],
          y="count",
          text="count",
          color="count",
          color_continuous_scale="Blues",
      )
      fig_bar.update_layout(
          margin=dict(t=20, b=20, l=20, r=20),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
          coloraxis_showscale=False,
      )

      selected_bar = st.plotly_chart(
          fig_bar,
          use_container_width=True,
          key="bar_plot",
          on_select="rerun",
      )

      if (
          selected_bar
          and "selection" in selected_bar
          and selected_bar["selection"]["points"]
      ):
        selected_points = [
            p["x"] for p in selected_bar["selection"]["points"]
        ]
        st.session_state.selected_filters[cat_columns[1]] = selected_points
        st.rerun()

    # --- มุมมองที่ 3: กราฟเส้น (Line Chart) แสดงแนวโน้มเรื่องที่ 3 ---
    with c3:
      st.subheader(f"📈 แนวโน้มตาม: {cat_columns[2]}")
      line_data = (
          filtered_df[cat_columns[2]].value_counts().reset_index().head(12)
      )
      line_data.columns = [cat_columns[2], "count"]
      line_data = line_data.sort_values(by=cat_columns[2])

      fig_line = px.line(
          line_data,
          x=cat_columns[2],
          y="count",
          markers=True,
          color_discrete_sequence=["#2563EB"],
      )
      fig_line.update_layout(
          margin=dict(t=20, b=20, l=20, r=20),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
      )

      selected_line = st.plotly_chart(
          fig_line,
          use_container_width=True,
          key="line_plot",
          on_select="rerun",
      )

      if (
          selected_line
          and "selection" in selected_line
          and selected_line["selection"]["points"]
      ):
        selected_points = [
            p["x"] for p in selected_line["selection"]["points"]
        ]
        st.session_state.selected_filters[cat_columns[2]] = selected_points
        st.rerun()
  else:
    st.warning("ข้อมูลมีคอลัมน์จัดกลุ่มไม่เพียงพอสำหรับการแสดงผลครบทุกมุมมอง")

  st.markdown("---")

  # ส่วนแสดงตารางข้อมูลรายละเอียดที่ถูกกรองข้ามกลุ่มเรียบร้อยแล้ว
  st.subheader(
      "📋 ตารางแสดงข้อมูลรายละเอียดทั้งหมด (รวมข้อมูลที่ผ่านการกรองข้ามมิติ)"
  )
  st.dataframe(filtered_df, use_container_width=True)

  # ปุ่มดาวน์โหลดข้อมูลที่กรองแล้วเป็นไฟล์ CSV
  csv_export = filtered_df.to_csv(index=False).encode("utf-8-sig")
  st.download_button(
      label="📥 ดาวน์โหลดข้อมูลชุดนี้ (.csv)",
      data=csv_export,
      file_name="cross_filtered_delivery_data.csv",
      mime="text/csv",
  )
