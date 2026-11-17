from pathlib import Path
import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='상품 대안 비교 | 시연 2', page_icon='▦', layout='wide')
st.markdown('<style>.block-container{max-width:1500px;padding-top:2rem} h1{letter-spacing:-1px} div[data-testid="stMetric"]{background:#fff;border-radius:12px;padding:16px} .eyebrow{color:#008c82;font-weight:700;letter-spacing:2px}</style>',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">DEMO 02 · PRODUCT EXPLORER</div>',unsafe_allow_html=True)
st.title('위고비 약제비 특약 상품 대안 비교 지도')
st.caption('급부액과 지급 한도에 따른 보장 · 보험료 · 손익 비교')
path=Path(__file__).parent/'data/results.csv'
upload=st.sidebar.file_uploader('결과 CSV 미리보기',type='csv',help='업로드는 현재 세션에만 적용됩니다. 영구 변경은 data/results.csv를 교체하세요.')
try:
 df=pd.read_csv(upload if upload is not None else path)
 required=['product_id','product_name','benefit_krw','limit_count','waiting_days','scenario','annual_premium_krw','expected_count','expected_benefit_pv_krw','profit_npv_krw','benefit_ae','max_funding_gap_krw','data_status','source_note']
 missing=set(required)-set(df.columns)
 if missing: raise ValueError('필수 열 누락: '+', '.join(sorted(missing)))
 nums=required[2:5]+required[6:12]
 for c in nums: df[c]=pd.to_numeric(df[c],errors='raise')
 if not np.isfinite(df[nums].to_numpy()).all(): raise ValueError('숫자 열에는 빈칸/무한값을 사용할 수 없습니다.')
 if df[required].isna().any().any(): raise ValueError('필수 열에 빈칸이 있습니다.')
 if df.duplicated(['product_id','scenario']).any(): raise ValueError('상품 ID·시나리오 중복입니다.')
 if set(df.scenario)!= {'기준','이용 증가'}: raise ValueError('시나리오는 기준/이용 증가 두 가지여야 합니다.')
 for pid,g in df.groupby('product_id'):
  if len(g)!=2: raise ValueError(f'{pid}: 두 시나리오가 필요합니다.')
  for c in ['product_name','benefit_krw','limit_count','waiting_days','annual_premium_krw']:
   if g[c].nunique()!=1: raise ValueError(f'{pid}: {c}는 시나리오 간 같아야 합니다.')
 if (df[[c for c in nums if c!='profit_npv_krw']]<0).any().any(): raise ValueError('손익 외 숫자는 음수일 수 없습니다.')
 if (df.expected_count>df.limit_count).any(): raise ValueError('기대 지급 횟수가 통산 한도를 초과합니다.')
 if df[df.scenario=='기준'].duplicated(['waiting_days','limit_count','benefit_krw']).any(): raise ValueError('동일 설계 조건이 중복됩니다.')
except Exception as e:
 st.error(f'CSV를 읽을 수 없습니다: {e}');st.stop()
if df.data_status.str.contains('가상').any(): st.warning('화면 검토용 가상 데이터 · 실제 보험료, 수익성 또는 상품 승인 근거가 아닙니다.')
else: st.info('데이터 구분: '+ ' / '.join(df.data_status.unique())+' · 업로드된 값의 타당성은 별도 검토가 필요합니다.')
st.caption('10년 만기 · 10년납 | 28일분 적격 조제당 정액 지급 | 환급금 없음 | 금액: 가입자 1인당 | 연령·성별·산출 기준일: 미설정')
st.sidebar.header('비교 조건')
wait=st.sidebar.radio('대기기간',sorted(df.waiting_days.unique()),index=len(df.waiting_days.unique())-1,format_func=lambda x:f'{x:g}일')
scenario=st.sidebar.radio('경험 시나리오',['기준','이용 증가'])
labels={'월 환산 보험료':'monthly','기대 급부 PV':'expected_benefit_pv_krw','이익 NPV':'profit_npv_krw','급부 A/E':'benefit_ae'}
metric=st.sidebar.selectbox('지도 표시 지표',list(labels))
df['monthly']=df.annual_premium_krw/12
df['max_cover']=df.benefit_krw*df.limit_count
sub=df[(df.waiting_days==wait)&(df.scenario==scenario)].sort_values(['limit_count','benefit_krw'])
if sub.empty: st.info('해당 조건에 데이터가 없습니다.');st.stop()
ids=sub.product_id.tolist()
if st.session_state.get('product') not in ids: st.session_state.product=ids[min(1,len(ids)-1)]
def choose(pid): st.session_state.product=pid
fmt=lambda v:f'{v:,.0f}원'
left,right=st.columns([2.2,1])
with left:
 st.subheader('상품 대안')
 st.caption(f'대기기간 {wait:g}일 · {scenario} · {len(sub)}개 상품')
 for limit,g in sub.groupby('limit_count'):
  st.markdown(f'**통산 {limit:g}회 지급**')
  cols=st.columns(len(g))
  for col,(_,r) in zip(cols,g.iterrows()):
   with col,st.container(border=True):
    st.caption(f'1회 {r.benefit_krw/10000:g}만 원')
    st.button(r.product_name+(' ✓' if r.product_id==st.session_state.product else ''),key=r.product_id,on_click=choose,args=(r.product_id,),use_container_width=True,type='primary' if r.product_id==st.session_state.product else 'secondary')
    st.markdown(f'최대 보장 **{r.max_cover/10000:g}만 원**')
    value=r[labels[metric]]
    st.metric(metric,f'{value:.2f}' if metric=='급부 A/E' else fmt(value))
 st.caption('색상 지도: 선택 지표에 따른 값의 크기. 상품의 판매 가능 여부를 의미하지 않습니다.')
 field=labels[metric]
 pivot=sub.pivot(index='limit_count',columns='benefit_krw',values=field).sort_index()
 allvals=df[field]
 zmin,zmax=float(allvals.min()),float(allvals.max())
 if field=='profit_npv_krw': zmax=max(abs(zmin),abs(zmax),1);zmin=-zmax
 fig=go.Figure(go.Heatmap(z=pivot.values,x=[f'{v/10000:g}만 원' for v in pivot.columns],y=[f'{v:g}회' for v in pivot.index],zmin=zmin,zmax=zmax,colorscale='RdBu' if field=='profit_npv_krw' else 'Blues',text=[[f'{v:,.2f}' if field=='benefit_ae' else f'{v:,.0f}원' for v in row] for row in pivot.values],texttemplate='%{text}',hovertemplate='1회 급부 %{x} · 한도 %{y}<br>%{text}<extra></extra>'))
 fig.update_layout(height=260,margin=dict(l=10,r=10,t=10,b=10),xaxis_title='1회 급부액',yaxis_title='통산 지급 한도')
 st.plotly_chart(fig,use_container_width=True)
 st.caption('같은 지표의 색상 범위는 모든 대기기간·경험 시나리오에서 고정됩니다.')
with right:
 st.subheader('선택 상품 상세')
 pid=st.session_state.product;r=sub[sub.product_id==pid].iloc[0]
 st.markdown(f'### {html.escape(r.product_name)} · {wait:g}일')
 data={'1회 급부액':fmt(r.benefit_krw),'통산 지급 한도':f'{r.limit_count:g}회','통산 최대 보장액':fmt(r.max_cover),'연납 예시 보험료':fmt(r.annual_premium_krw),'월 환산 보험료':fmt(r.monthly),'기대 지급 횟수':f'{r.expected_count:.2f}회','기대 급부 PV':fmt(r.expected_benefit_pv_krw),'급부 A/E':f'{r.benefit_ae:.2f}','최대 자금 부족액':fmt(r.max_funding_gap_krw)}
 for s in ['기준','이용 증가']: data[s+' 이익 NPV']=fmt(df[(df.product_id==pid)&(df.scenario==s)].iloc[0].profit_npv_krw)
 st.table(pd.DataFrame(data.items(),columns=['항목','값']).set_index('항목'))
 st.caption('월 환산액 = 연납 보험료 ÷ 12. 실제 월납 보험료가 아닙니다.')
st.subheader('두 상품 나란히 비교')
selected=st.multiselect('비교할 상품 (최대 2개)',ids,default=ids[1:2]+ids[-2:-1] if len(ids)>=5 else ids[:2],max_selections=2,key=f'compare_{wait}',format_func=lambda p:df.drop_duplicates('product_id').set_index('product_id').loc[p,'product_name'])
show=sub[sub.product_id.isin(selected)][['product_name','benefit_krw','limit_count','max_cover','monthly','expected_benefit_pv_krw','profit_npv_krw','benefit_ae']].rename(columns={'product_name':'상품','benefit_krw':'1회 급부액(원)','limit_count':'지급 한도(회)','max_cover':'최대 보장(원)','monthly':'월 환산액(원)','expected_benefit_pv_krw':'기대 급부 PV(원)','profit_npv_krw':'이익 NPV(원)','benefit_ae':'급부 A/E'})
st.dataframe(show.set_index('상품').T,use_container_width=True)
with st.expander('데이터 출처 · 가상값 구성 · 해석 안내'):
 st.write('\n\n'.join(df.source_note.unique()))
 st.write('가상값은 12회 한도 기대 횟수 3.2회, 24회 한도 4.4회를 출발점으로 설정했습니다. 180일 대기는 0.9배, 급부 현가는 횟수×급부액×0.88입니다. 연납 보험료는 (급부 PV+20,000)/(0.8×8.5)를 100원 단위 반올림했습니다. 이익은 보험료×8.5×0.8−20,000−경험 급부 PV입니다. 이용 증가 시 급부는 12회 한도 1.25배, 24회 한도 1.45배입니다.')
 st.write('최대 자금 부족액도 임의의 화면 확인용 값(급부 PV×0.45−연보험료×0.8의 양수 부분)이며 연도별 현금흐름에서 산출한 결과가 아닙니다. 실제 분석 시 모든 해당 열을 교체하세요. 사망보험금 감소액은 특약 보험료에서 차감하지 않습니다.')
st.download_button('현재 전체 결과 CSV 다운로드',df[required].to_csv(index=False).encode('utf-8-sig'),'demo2_results.csv','text/csv')
