import pandas as pd
import re
import streamlit as st

st.set_page_config(page_title="데이터 정제", layout="wide")


def parse_time_to_minutes(val):
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    numbers = re.findall(r"\d+", val_str)
    if not numbers:
        return None
    if "시간" in val_str and "분" in val_str:
        return int(numbers[0]) * 60 + int(numbers[1])
    elif "시간" in val_str:
        return int(numbers[0]) * 60
    else:
        return int(numbers[0])


def clean_grade(val):
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    match = re.search(r"\d+", val_str)
    if match:
        return int(match.group())
    words = {"일": 1, "이": 2, "삼": 3, "사": 4}
    for k, v in words.items():
        if k in val_str:
            return v
    return None


def clean_college(val):
    if pd.isna(val):
        return "기타"
    val_str = str(val).strip()
    if "인문" in val_str:
        return "인문대학"
    elif "사과" in val_str or "사회" in val_str:
        return "사회과학대학"
    elif "경통" in val_str or "경제" in val_str:
        return "경제통상대학"
    elif "경영" in val_str:
        return "경영대학"
    elif "사범" in val_str:
        return "사범대학"
    else:
        return "기타"


def process_cleaning(df_raw, max_time_limit, missing_option):
    df_clean = df_raw.copy()
    logs = []

    # 1. 열 제목 축소
    col_mapping = {
        df_clean.columns[0]: "타임스탬프",
        df_clean.columns[1]: "성별",
        df_clean.columns[2]: "학년",
        df_clean.columns[3]: "소속단과대학",
        df_clean.columns[4]: "AI사용시간",
        df_clean.columns[5]: "Q1(활용)",
        df_clean.columns[6]: "Q2(신뢰)",
        df_clean.columns[7]: "Q3(학업정직성)",
        df_clean.columns[8]: "Q4(개인정보)",
        df_clean.columns[9]: "Q5(자율성)",
        df_clean.columns[10]: "Q6(정직성역)",
        df_clean.columns[11]: "서술형",
    }
    df_clean.rename(columns=col_mapping, inplace=True)
    logs.append({"정제 단계": "1. 열 제목 변경", "상세 내용": "표준 열 이름(타임스탬프, 성별, 학년, 소속단과대학, AI사용시간, Q1~Q6, 서술형)으로 축소"})

    # 2. 중복 제거 (타임스탬프 제외 모든 열)
    check_cols = [c for c in df_clean.columns if c != "타임스탬프"]
    before_dup = len(df_clean)
    df_clean.drop_duplicates(subset=check_cols, keep="first", inplace=True)
    dup_removed = before_dup - len(df_clean)
    logs.append({"정제 단계": "2. 중복 제거", "상세 내용": f"타임스탬프 제외 중복 행 {dup_removed}건 제거"})

    # 3. 학년 표기 통일
    df_clean["학년"] = df_clean["학년"].apply(clean_grade)
    logs.append({"정제 단계": "3. 학년 통일", "상세 내용": "숫자 형식(1, 2, 3...)으로 변환 완료"})

    # 4. 단과대학 분류
    df_clean["소속단과대학"] = df_clean["소속단과대학"].apply(clean_college)
    logs.append({"정제 단계": "4. 단과대학 분류", "상세 내용": "인문/사회과학/경제통상/경영/사범/기타 대학으로 재분류"})

    # 5. 사용시간 이상치 처리 (분 단위 변환 및 사이드바 기준 적용)
    df_clean["AI사용시간"] = df_clean["AI사용시간"].apply(parse_time_to_minutes)
    before_outlier = len(df_clean)
    df_clean = df_clean[
        df_clean["AI사용시간"].isna() | (df_clean["AI사용시간"] <= max_time_limit)
    ]
    outlier_removed = before_outlier - len(df_clean)
    logs.append(
        {
            "정제 단계": "5. 이상치 처리",
            "상세 내용": f"분 단위 수치 변환 및 허용 기준({max_time_limit}분) 초과 {outlier_removed}건 제거",
        }
    )

    # 6. 결측치 처리
    missing_summary = df_clean.isna().sum().to_dict()
    if missing_option == "행삭제":
        before_na = len(df_clean)
        df_clean.dropna(subset=["성별", "학년", "소속단과대학", "AI사용시간"], inplace=True)
        na_removed = before_na - len(df_clean)
        logs.append(
            {
                "정제 단계": "6. 결측치 처리",
                "상세 내용": f"행삭제 선택: 주요 열 결측 행 {na_removed}건 삭제 완료",
            }
        )
    else:
        logs.append(
            {
                "정제 단계": "6. 결측치 처리",
                "상세 내용": "그대로 두기 선택: 결측치 보존",
            }
        )

    # 7. 역문항 점수 재계산 (Q6R = 6 - Q6)
    if "Q6" in df_clean.columns:
        df_clean["Q6"] = pd.to_numeric(df_clean["Q6"], errors="coerce")
        df_clean["Q6R"] = 6 - df_clean["Q6"]
        logs.append({"정제 단계": "7. 점수 재계산", "상세 내용": "Q6R = 6 - Q6 역문항 계산 완료"})

    return df_clean, pd.DataFrame(logs), missing_summary


# 사이드바 설정
st.sidebar.header("설정 메뉴")
max_time_limit = st.sidebar.slider(
    "AI 사용 시간 이상치 허용 범위 (분)", min_value=60, max_value=720, value=300, step=30
)
missing_option = st.sidebar.radio(
    "빈칸(결측치) 처리 방식 선택", options=["그대로 두기", "행삭제"]
)

# 메인 화면
st.title("설문 데이터 정제")

uploaded_file = st.file_uploader(
    "구글 설문지 CSV (survey_raw.csv) 파일을 업로드하세요.", type=["csv"]
)

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    st.session_state["raw_df"] = df_raw

    st.subheader("1. 원본 데이터 확인")
    st.metric(label="전체 설문 응답자 수", value=f"{len(df_raw)} 명")
    st.dataframe(df_raw, use_container_width=True)

    # 데이터 정제 수행
    df_clean, df_logs, missing_summary = process_cleaning(
        df_raw, max_time_limit, missing_option
    )
    st.session_state["clean_df"] = df_clean

    st.subheader("2. 데이터 정제 결과 카드")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="원본 응답자 수", value=f"{len(df_raw)} 명")
    col2.metric(label="정제 후 응답자 수", value=f"{len(df_clean)} 명")
    col3.metric(label="제거된 응답자 수", value=f"{len(df_raw) - len(df_clean)} 명")

    st.markdown("**열별 결측치(빈칸) 수**")
    st.json(missing_summary)

    st.subheader("3. 정제 기록")
    st.table(df_logs)

    st.subheader("4. 최종 정제된 데이터")
    st.dataframe(df_clean, use_container_width=True)

    # CSV 다운로드
    csv_data = df_clean.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="정제된 데이터 CSV 내려받기",
        data=csv_data,
        file_name="survey_cleaned.csv",
        mime="text/csv",
    )
else:
    st.info("상단의 파일 업로더를 이용해 설문 CSV 파일을 업로드해 주세요.")