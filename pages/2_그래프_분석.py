import pandas as pd
import streamlit as st

st.set_page_config(page_title="그래프 분석", layout="wide")


def standardize_dataframe(df):
    """업로드된 데이터프레임의 열 이름을 표준화하여 KeyError 방지"""
    new_df = df.copy()

    # 열 이름에 특정 키워드가 포함되어 있으면 표준 이름으로 변경
    col_mapping = {}
    for col in new_df.columns:
        col_str = str(col).strip()
        if "타임스탬프" in col_str or "Timestamp" in col_str:
            col_mapping[col] = "타임스탬프"
        elif "성별" in col_str:
            col_mapping[col] = "성별"
        elif "학년" in col_str:
            col_mapping[col] = "학년"
        elif "단과" in col_str or "소속" in col_str:
            col_mapping[col] = "소속단과대학"
        elif "사용 시간" in col_str or "사용시간" in col_str:
            col_mapping[col] = "AI사용시간"

    if col_mapping:
        new_df.rename(columns=col_mapping, inplace=True)

    return new_df


def load_dataset():
    """세션 상태에서 정제된 데이터를 불러오고 표준화 수행"""
    if "clean_df" in st.session_state and st.session_state["clean_df"] is not None:
        df = st.session_state["clean_df"]
        return standardize_dataframe(df)
    return None


def calculate_ethics_score(df):
    """윤리 관련 문항 평균 점수 계산"""
    ethics_cols = [c for c in ["Q3", "Q4", "Q5", "Q6R"] if c in df.columns]
    if ethics_cols:
        return (
            df[ethics_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1).mean()
        )
    return 0.0


def display_metrics(df):
    """요약 지표 출력 (AI사용시간 열 존재 여부 안전 검사)"""
    col1, col2, col3 = st.columns(3)
    col1.metric("유효 응답", f"{len(df)} 명")

    if "AI사용시간" in df.columns:
        mean_time = pd.to_numeric(df["AI사용시간"], errors="coerce").mean()
        col2.metric("평균 AI 사용 시간", f"{mean_time:.1f} 분")
    else:
        col2.metric("평균 AI 사용 시간", "데이터 없음")

    ethics_avg = calculate_ethics_score(df)
    col3.metric("AI 윤리의식 평균", f"{ethics_avg:.2f} / 5.0")


def display_before_after_comparison(df_raw, df_clean):
    """정제 전후 단과대학별 응답자 수 비교"""
    st.subheader("정제 전후 단과대학별 응답자 수 비교")
    if df_raw is not None and "소속단과대학" in df_clean.columns:
        # 원본 데이터도 표준화 시도
        raw_std = standardize_dataframe(df_raw)
        if "소속단과대학" in raw_std.columns and "소속단과대학" in df_clean.columns:
            raw_counts = raw_std["소속단과대학"].value_counts()
            clean_counts = df_clean["소속단과대학"].value_counts()

            comp_df = pd.DataFrame({"정제 전": raw_counts, "정제 후": clean_counts}).fillna(0)
            st.bar_chart(comp_df, horizontal=True)
        else:
            st.write("원본 데이터에서 단과대학 열을 찾을 수 없습니다.")
            st.bar_chart(df_clean["소속단과대학"].value_counts(), horizontal=True)
    else:
        st.write("원본 데이터가 없어 정제 후 데이터만 표시합니다.")
        if "소속단과대학" in df_clean.columns:
            st.bar_chart(df_clean["소속단과대학"].value_counts(), horizontal=True)


def render_tab_demographics(df):
    """응답자 구성 탭 렌더링"""
    col1, col2 = st.columns(2)
    with col1:
        st.write("성별 구성")
        if "성별" in df.columns:
            st.bar_chart(df["성별"].value_counts(), horizontal=True)
        else:
            st.write("성별 데이터가 없습니다.")
    with col2:
        st.write("단과대학 구성")
        if "소속단과대학" in df.columns:
            st.bar_chart(df["소속단과대학"].value_counts(), horizontal=True)
        else:
            st.write("단과대학 데이터가 없습니다.")


def render_tab_item_means(df):
    """문항별 평균 점수 탭 렌더링"""
    st.write("문항별 평균 점수")
    q_cols = [c for c in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q6R"] if c in df.columns]
    if q_cols:
        means = df[q_cols].apply(pd.to_numeric, errors="coerce").mean().round(2)
        means_df = pd.DataFrame({"문항": means.index, "평균점수": means.values})
        st.bar_chart(means_df.set_index("문항"), horizontal=True)
    else:
        st.write("분석할 문항 데이터가 없습니다.")


def render_tab_group_comparison(df):
    """집단 비교 탭 렌더링"""
    st.write("집단별 비교 (학년 및 단과대학)")
    q_cols = [c for c in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q6R"] if c in df.columns]
    num_df = df.copy()
    for c in q_cols:
        num_df[c] = pd.to_numeric(num_df[c], errors="coerce")

    if "학년" in num_df.columns and q_cols:
        st.write("1. 학년별 평균 및 인원 수")
        grade_grp = (
            num_df.groupby("학년")[q_cols]
            .mean()
            .round(2)
            .assign(인원수=num_df.groupby("학년").size())
        )
        st.dataframe(grade_grp)

    if "소속단과대학" in num_df.columns and q_cols:
        st.write("2. 단과대학별 평균 및 인원 수")
        college_grp = (
            num_df.groupby("소속단과대학")[q_cols]
            .mean()
            .round(2)
            .assign(인원수=num_df.groupby("소속단과대학").size())
        )
        st.dataframe(college_grp)


def render_tab_time_and_score(df):
    """사용 시간과 점수 비교 탭 렌더링"""
    st.write("AI 사용 시간과 문항 점수 간 비교")
    if "AI사용시간" not in df.columns:
        st.write("AI사용시간 데이터가 없습니다.")
        return

    q_cols = [c for c in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q6R"] if c in df.columns]
    if not q_cols:
        st.write("문항 데이터가 없습니다.")
        return

    num_df = df.copy()
    for c in q_cols:
        num_df[c] = pd.to_numeric(num_df[c], errors="coerce")
    num_df["AI사용시간"] = pd.to_numeric(num_df["AI사용시간"], errors="coerce")

    selected_q = st.selectbox("분석할 문항 선택", q_cols)
    chart_data = num_df[["AI사용시간", selected_q]].dropna().set_index("AI사용시간")
    st.line_chart(chart_data)


# 메인 실행 흐름
st.title("설문 데이터 그래프 분석")

df_clean = load_dataset()

if df_clean is None:
    st.warning(
        "정제된 데이터가 없습니다. 1_데이터_정제 페이지에서 먼저 정제를 진행해 주세요."
    )
    uploaded_clean = st.file_uploader(
        "정제된 CSV 파일 업로드", type=["csv"], key="analysis_uploader"
    )
    if uploaded_clean is not None:
        raw_uploaded = pd.read_csv(uploaded_clean)
        df_clean = standardize_dataframe(raw_uploaded)
        st.session_state["clean_df"] = df_clean

if df_clean is not None:
    # 1. 요약 지표
    display_metrics(df_clean)
    st.divider()

    # 2. 정제 전후 비교
    df_raw = st.session_state.get("raw_df", None)
    display_before_after_comparison(df_raw, df_clean)
    st.divider()

    # 3. 4개 탭 분석
    tab1, tab2, tab3, tab4 = st.tabs(
        ["응답자 구성", "문항별 평균", "집단 비교", "사용 시간과 점수"]
    )

    with tab1:
        render_tab_demographics(df_clean)
    with tab2:
        render_tab_item_means(df_clean)
    with tab3:
        render_tab_group_comparison(df_clean)
    with tab4:
        render_tab_time_and_score(df_clean)