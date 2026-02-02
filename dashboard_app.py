import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Loan Collection Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force light/white theme with black text
st.markdown("""
    <style>
    /* Fix metric boxes - make values visible */
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 700;
        font-size: 28px !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #CCCCCC !important;
        font-weight: 600;
        font-size: 14px !important;
    }
    
    /* Make metric containers have dark background */
    [data-testid="stMetric"] {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    /* Sidebar text visibility */
    [data-testid="stSidebar"] * {
        color: inherit;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to apply dark theme to all charts
def apply_chart_theme(fig):
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',  # Transparent
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent
        font=dict(color='white', size=12),
        title_font=dict(color='white', size=16, family='Arial', weight='bold'),
        xaxis=dict(gridcolor='#444444', color='white'),
        yaxis=dict(gridcolor='#444444', color='white'),
        legend=dict(font=dict(color='white'))
    )
    return fig

# Load data with caching
@st.cache_data
def load_data():
    df = pd.read_csv('Vinayna_Latest.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    return df

# Function to find DPD pattern customers
@st.cache_data
def find_dpd_pattern_customers(df):
    """
    Find customers with PTP -> DPD increase -> DPD decrease pattern
    """
    # Sort by customer and date
    df_sorted = df.sort_values(['DisbursementID', 'Date']).reset_index(drop=True)
    
    # Calculate DPD change
    df_sorted['DPD_Previous'] = df_sorted.groupby('DisbursementID')['NumberOfDaysPastDue'].shift(1)
    df_sorted['DPD_Change'] = df_sorted['NumberOfDaysPastDue'] - df_sorted['DPD_Previous']
    
    # Categorize changes
    df_sorted['DPD_Increased'] = df_sorted['DPD_Change'] > 0
    df_sorted['DPD_Decreased'] = df_sorted['DPD_Change'] < 0
    
    # Customers with PTP
    customers_with_ptp = df_sorted[
        (df_sorted['PTP Status'].notna()) & 
        (df_sorted['PTP Status'] != 'No PTP')
    ]['DisbursementID'].unique()
    
    # Find pattern customers
    target_customers = []
    customer_summary_list = []
    
    for customer_id in customers_with_ptp:
        customer_data = df_sorted[df_sorted['DisbursementID'] == customer_id].copy()
        
        has_dpd_increase = customer_data['DPD_Increased'].any()
        has_dpd_decrease = customer_data['DPD_Decreased'].any()
        
        if has_dpd_increase and has_dpd_decrease:
            increase_dates = customer_data[customer_data['DPD_Increased'] == True]['Date'].tolist()
            decrease_dates = customer_data[customer_data['DPD_Decreased'] == True]['Date'].tolist()
            
            for inc_date in increase_dates:
                subsequent_decreases = [dec_date for dec_date in decrease_dates if dec_date > inc_date]
                if subsequent_decreases:
                    target_customers.append(customer_id)
                    
                    customer_summary_list.append({
                        'DisbursementID': customer_id,
                        'Customer_Name': customer_data['Customer Name'].iloc[0] if 'Customer Name' in customer_data.columns else customer_data['CustomerName'].iloc[0],
                        'Branch': customer_data['Branch'].iloc[0],
                        'Total_Records': len(customer_data),
                        'DPD_Increases': int(customer_data['DPD_Increased'].sum()),
                        'DPD_Decreases': int(customer_data['DPD_Decreased'].sum()),
                        'Max_DPD': int(customer_data['NumberOfDaysPastDue'].max()),
                        'Current_DPD': int(customer_data['NumberOfDaysPastDue'].iloc[-1]),
                        'Total_Collection': float(customer_data['Collection Amount'].sum()),
                        'Total_PTP_Amount': float(customer_data['PTP Amount'].sum()),
                    })
                    break
    
    summary_df = pd.DataFrame(customer_summary_list) if customer_summary_list else pd.DataFrame()
    
    return summary_df, df_sorted, target_customers

# Main title
st.title("📊 Loan Collection Analytics Dashboard")
st.markdown("---")

# Load data
try:
    df = load_data()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Add navigation option in sidebar
    st.sidebar.markdown("---")
    page_selection = st.sidebar.radio(
        "📋 Navigation",
        ["Dashboard", "DPD Wise Transition Customer"],
        index=0
    )
    st.sidebar.markdown("---")
    
    # Date filter
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Branch filter
    branches = ['All Branches'] + sorted(df['Branch'].dropna().unique().tolist())
    selected_branch = st.sidebar.selectbox("Select Branch", branches)
    
    # PTP Status filter
    ptp_statuses = ['All Status'] + sorted(df['PTP Status'].dropna().unique().tolist())
    selected_ptp_status = st.sidebar.selectbox("Select PTP Status", ptp_statuses)
    
    # Loan Status filter
    loan_status = st.sidebar.radio("Loan Status", ['All', 'Active Only', 'Inactive Only'])
    
    # Apply filters
    filtered_df = df.copy()
    
    # Date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[(filtered_df['Date'].dt.date >= start_date) & 
                                  (filtered_df['Date'].dt.date <= end_date)]
    
    # Branch filter
    if selected_branch != 'All Branches':
        filtered_df = filtered_df[filtered_df['Branch'] == selected_branch]
    
    # PTP Status filter
    if selected_ptp_status != 'All Status':
        filtered_df = filtered_df[filtered_df['PTP Status'] == selected_ptp_status]
    
    # Loan Status filter
    if loan_status == 'Active Only':
        filtered_df = filtered_df[filtered_df['IsActive'] == True]
    elif loan_status == 'Inactive Only':
        filtered_df = filtered_df[filtered_df['IsActive'] == False]
    
    # Display filter info
    st.sidebar.markdown("---")
    st.sidebar.info(f"📅 Showing data from {filtered_df['Date'].min().date()} to {filtered_df['Date'].max().date()}")
    st.sidebar.info(f"📊 Total Records: {len(filtered_df):,}")
    
    # ============================================================================
    # PAGE ROUTING
    # ============================================================================
    
    if page_selection == "DPD Wise Transition Customer":
        # ============================================================================
        # DPD WISE TRANSITION CUSTOMER PAGE
        # ============================================================================
        
        st.header("🔄 DPD Wise Transition Customer Analysis")
        st.markdown("""
        **Find customers who:**
        1. Made a Promise to Pay (PTP) 📝
        2. Broke the promise (DPD increased) ⬆️
        3. Later made payment (DPD decreased) ⬇️
        """)
        
        # Run analysis
        with st.spinner("Analyzing DPD transition patterns..."):
            pattern_summary, df_with_changes, pattern_customers = find_dpd_pattern_customers(filtered_df)
        
        if len(pattern_summary) > 0:
            
            # Display total count
            st.success(f"✓ Found **{len(pattern_customers)}** customers with DPD transition pattern!")
            
            st.markdown("---")
            
            # Section 1: Show all pattern customers list
            st.subheader("📋 All DPD Transition Customers")
            
            # Format the display
            display_summary = pattern_summary.copy()
            display_summary['Total_Collection'] = display_summary['Total_Collection'].apply(lambda x: f"₹{x:,.2f}")
            display_summary['Total_PTP_Amount'] = display_summary['Total_PTP_Amount'].apply(lambda x: f"₹{x:,.2f}")
            
            # Rename columns for display
            display_summary.columns = [
                'Disbursement ID', 'Customer Name', 'Branch', 'Total Records',
                'DPD Increases', 'DPD Decreases', 'Max DPD', 'Current DPD',
                'Total Collection', 'Total PTP Amount'
            ]
            
            # Display the table
            st.dataframe(
                display_summary,
                width='stretch',
                height=400
            )
            
            # Download button for the list
            csv = pattern_summary.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Customer List (CSV)",
                data=csv,
                file_name=f'dpd_transition_customers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
            )
            
            st.markdown("---")
            
            # Section 2: Search for specific customer
            st.subheader("🔍 Search Customer Timeline")
            
            # Create search interface
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Dropdown to select customer
                selected_customer = st.selectbox(
                    "Select Customer ID",
                    options=[''] + [str(cust) for cust in pattern_customers],
                    format_func=lambda x: 'Select a customer...' if x == '' else x,
                    key='dpd_customer_select'
                )
            
            with col2:
                st.write("")  # Spacer
                st.write("")  # Spacer
                search_button = st.button("🔍 Show Timeline", width='stretch', key='dpd_search_btn')
            
            # OR text input for direct search
            st.write("**OR**")
            search_input = st.text_input("Enter Customer ID manually:", placeholder="e.g., 0270001375", key='dpd_search_input')
            
            # Determine which customer to show
            customer_to_show = None
            if search_button and selected_customer != '':
                customer_to_show = selected_customer
            elif search_input:
                # Try to match customer ID flexibly
                search_clean = str(search_input).replace('.0', '').lstrip('0')
                matched = False
                for cust in pattern_customers:
                    cust_clean = str(cust).replace('.0', '').lstrip('0')
                    if cust_clean == search_clean:
                        customer_to_show = cust
                        matched = True
                        break
                if not matched:
                    st.error(f"❌ Customer ID '{search_input}' not found in DPD transition customers list!")
            
            # Display customer timeline if selected
            if customer_to_show:
                st.markdown("---")
                
                # Clean the customer ID for display
                customer_to_show_display = str(customer_to_show).replace('.0', '')
                st.subheader(f"📊 Detailed Timeline: {customer_to_show_display}")
                
                # Get customer data - handle both string and numeric formats
                customer_to_show_clean = str(customer_to_show).replace('.0', '')
                customer_data = df_with_changes[
                    (df_with_changes['DisbursementID'].astype(str) == customer_to_show_clean) |
                    (df_with_changes['DisbursementID'].astype(str) == str(customer_to_show)) |
                    (df_with_changes['DisbursementID'].astype(str).str.lstrip('0') == customer_to_show_clean.lstrip('0'))
                ].copy()
                
                if len(customer_data) == 0:
                    st.error(f"❌ No data found for customer {customer_to_show}")
                    st.stop()
                
                # Customer summary box - match with flexible comparison
                customer_info_match = pattern_summary[
                    (pattern_summary['DisbursementID'].astype(str) == customer_to_show_clean) |
                    (pattern_summary['DisbursementID'].astype(str) == str(customer_to_show)) |
                    (pattern_summary['DisbursementID'].astype(str).str.replace('.0', '') == customer_to_show_clean)
                ]
                
                if len(customer_info_match) == 0:
                    st.error(f"❌ Customer info not found for {customer_to_show_display}")
                    st.stop()
                
                customer_info = customer_info_match.iloc[0]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Customer Name", customer_info['Customer_Name'])
                with col2:
                    st.metric("Branch", customer_info['Branch'])
                with col3:
                    st.metric("Max DPD", f"{customer_info['Max_DPD']} days")
                with col4:
                    st.metric("Current DPD", f"{customer_info['Current_DPD']} days")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("DPD Increases", customer_info['DPD_Increases'])
                with col2:
                    st.metric("DPD Decreases", customer_info['DPD_Decreases'])
                with col3:
                    st.metric("Total Collection", f"₹{customer_info['Total_Collection']:,.2f}")
                with col4:
                    st.metric("Total PTP Amount", f"₹{customer_info['Total_PTP_Amount']:,.2f}")
                
                st.markdown("---")
                
                # Display timeline table
                st.write("**Complete Timeline:**")
                
                # Determine which Customer Name column exists
                customer_name_col = 'Customer Name' if 'Customer Name' in customer_data.columns else 'CustomerName'
                
                # Select columns to display
                display_cols = [
                    'Date', 
                    customer_name_col,
                    'Branch',
                    'NumberOfDaysPastDue', 
                    'DPD_Change', 
                    'PTP Status', 
                    'PTP Amount', 
                    'Collection Amount',
                    'Total Communications'
                ]
                
                # Filter only available columns
                available_cols = [col for col in display_cols if col in customer_data.columns]
                timeline_display = customer_data[available_cols].copy()
                
                # Format date and amounts
                timeline_display['Date'] = timeline_display['Date'].dt.date
                if 'PTP Amount' in timeline_display.columns:
                    timeline_display['PTP Amount'] = timeline_display['PTP Amount'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else 'N/A')
                if 'Collection Amount' in timeline_display.columns:
                    timeline_display['Collection Amount'] = timeline_display['Collection Amount'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else '₹0.00')
                
                # Rename columns for better display
                col_rename = {
                    'Date': 'Date',
                    customer_name_col: 'Customer Name',
                    'Branch': 'Branch',
                    'NumberOfDaysPastDue': 'DPD',
                    'DPD_Change': 'DPD Change',
                    'PTP Status': 'PTP Status',
                    'PTP Amount': 'PTP Amount',
                    'Collection Amount': 'Collection',
                    'Total Communications': 'Communications'
                }
                timeline_display = timeline_display.rename(columns=col_rename)
                
                # Highlight rows with DPD increase/decrease
                def highlight_dpd_change(row):
                    if 'DPD Change' in row.index and pd.notna(row['DPD Change']):
                        try:
                            dpd_val = float(str(row['DPD Change']).replace('₹', '').replace(',', ''))
                            if dpd_val > 0:
                                return ['background-color: #ffcccc'] * len(row)  # Red for increase
                            elif dpd_val < 0:
                                return ['background-color: #ccffcc'] * len(row)  # Green for decrease
                        except:
                            pass
                    return [''] * len(row)
                
                # Display with styling
                st.dataframe(
                    timeline_display,
                    width='stretch',
                    height=500
                )
                
                st.info("""
                **Legend:**
                - 🔴 Red background = DPD Increased (broke promise)
                - 🟢 Green background = DPD Decreased (made payment)
                """)
                
                # Download button for this customer
                customer_csv = customer_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download Timeline for {customer_to_show}",
                    data=customer_csv,
                    file_name=f'customer_{customer_to_show}_timeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                    key='dpd_download_btn'
                )

        else:
            st.warning("⚠️ No customers found with DPD transition pattern in filtered data.")
            st.info("Try adjusting the date range or filters to include more data.")
    
    else:
        # ============================================================================
        # MAIN DASHBOARD PAGE (Original Code)
        # ============================================================================
        
        # Calculate metrics
        total_unique_customers = filtered_df['DisbursementID'].nunique()
        total_communications = filtered_df['Total Communications'].sum()
        total_whatsapp_sent = filtered_df['WhatsApp'].sum()
        total_blaster_sent = filtered_df['Blaster'].sum()
        total_AI_Calls_sent = filtered_df['AI Calls'].sum()
        total_ptp_amount = filtered_df['PTP Amount'].sum()
        total_collection_amount = filtered_df['Collection Amount'].sum()
        total_overdue_amount = filtered_df['Overdue Amount'].sum()
        collection_rate = (total_collection_amount / total_overdue_amount * 100) if total_overdue_amount > 0 else 0
        
        # Section 1: Key Performance Indicators
        st.header("📈 Key Performance Indicators")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="👥 Unique Customers",
                value=f"{total_unique_customers:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="📞 Total Communications",
                value=f"{total_communications:,}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="💰 PTP Amount",
                value=f"₹{total_ptp_amount:,.0f}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="💵 Collection Amount",
                value=f"₹{total_collection_amount:,.0f}",
                delta=None
            )
        
        with col5:
            st.metric(
                label="📊 Collection Rate",
                value=f"{collection_rate:.2f}%",
                delta=None
            )
        
        st.markdown("---")
        
        # Section 2: Communication Breakdown
        st.header("📱 Communication Channel Breakdown")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="📱 WhatsApp Sent",
                value=f"{total_whatsapp_sent:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="📢 Blaster Sent",
                value=f"{total_blaster_sent:,}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="🤖 AI Calls Sent",
                value=f"{total_AI_Calls_sent:,}",
                delta=None
            )
        
        st.markdown("---")
        
        # Section 3: Collection Analysis by PTP Source
        st.header("💰 Collection Amount by PTP Source")
        
        collection_data = filtered_df[(filtered_df['Collection Amount'] > 0) & 
                                      (filtered_df['PTP Source'].notna())].copy()
        
        if len(collection_data) > 0:
            collection_by_source = collection_data.groupby('PTP Source')['Collection Amount'].sum().sort_values(ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Bar chart
                fig_bar = px.bar(
                    x=collection_by_source.index,
                    y=collection_by_source.values,
                    labels={'x': 'PTP Source', 'y': 'Collection Amount (₹)'},
                    title='Collection Amount by PTP Source',
                    color=collection_by_source.values,
                    color_continuous_scale='Blues',
                    text=collection_by_source.values
                )
                fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
                fig_bar = apply_chart_theme(fig_bar)
                fig_bar.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_bar, width='stretch')
            
            with col2:
                # Pie chart
                fig_pie = px.pie(
                    values=collection_by_source.values,
                    names=collection_by_source.index,
                    title='Collection Distribution by PTP Source',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie = apply_chart_theme(fig_pie)
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, width='stretch')
            
            # Detailed breakdown
            st.subheader("📋 Detailed Collection Breakdown")
            collection_count = collection_data.groupby('PTP Source').agg({
                'Collection Amount': ['count', 'sum', 'mean']
            }).round(2)
            collection_count.columns = ['Number of Collections', 'Total Amount (₹)', 'Average Amount (₹)']
            collection_count = collection_count.sort_values('Total Amount (₹)', ascending=False)
            collection_count['Total Amount (₹)'] = collection_count['Total Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
            collection_count['Average Amount (₹)'] = collection_count['Average Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(collection_count, width='stretch')
        else:
            st.warning("No collection data available for the selected filters.")
        
        st.markdown("---")
        
        # Section 4: Communication Channel Effectiveness
        st.header("📊 Communication Channel Effectiveness")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Communication volume comparison
            comm_data = pd.DataFrame({
                'Channel': ['WhatsApp', 'Blaster', 'AI Calls'],
                'Count': [total_whatsapp_sent, total_blaster_sent, total_AI_Calls_sent]
            })
            
            fig_comm = px.bar(
                comm_data,
                x='Channel',
                y='Count',
                title='Communication Volume by Channel',
                color='Count',
                color_continuous_scale='Viridis',
                text='Count'
            )
            fig_comm.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_comm = apply_chart_theme(fig_comm)
            fig_comm.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_comm, width='stretch')
        
        with col2:
            # Collection by communication channel
            if len(collection_data) > 0:
                fig_comm_collect = px.scatter(
                    collection_data.groupby('PTP Source').agg({
                        'Collection Amount': 'sum',
                        'DisbursementID': 'count'
                    }).reset_index(),
                    x='DisbursementID',
                    y='Collection Amount',
                    size='Collection Amount',
                    color='PTP Source',
                    title='Collections vs Number of Transactions',
                    labels={'DisbursementID': 'Number of Transactions', 'Collection Amount': 'Total Collection (₹)'},
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_comm_collect = apply_chart_theme(fig_comm_collect)
                fig_comm_collect.update_layout(height=400)
                st.plotly_chart(fig_comm_collect, width='stretch')
        
        st.markdown("---")
        
        # Section 5: PTP Status Breakdown
        st.header("🎯 PTP (Promise to Pay) Status Analysis")
        
        ptp_data = filtered_df[filtered_df['PTP Status'].notna()]
        
        if len(ptp_data) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                ptp_status_count = ptp_data['PTP Status'].value_counts()
                fig_ptp = px.pie(
                    values=ptp_status_count.values,
                    names=ptp_status_count.index,
                    title='PTP Status Distribution',
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    hole=0.3
                )
                fig_ptp.update_traces(textposition='inside', textinfo='percent+label+value')
                fig_ptp = apply_chart_theme(fig_ptp)
                fig_ptp.update_layout(height=400)
                st.plotly_chart(fig_ptp, width='stretch')
            
            with col2:
                ptp_amount_by_status = ptp_data.groupby('PTP Status')['PTP Amount'].sum().sort_values(ascending=False)
                fig_ptp_amount = px.bar(
                    x=ptp_amount_by_status.index,
                    y=ptp_amount_by_status.values,
                    title='PTP Amount by Status',
                    labels={'x': 'PTP Status', 'y': 'PTP Amount (₹)'},
                    color=ptp_amount_by_status.values,
                    color_continuous_scale='Oranges',
                    text=ptp_amount_by_status.values
                )
                fig_ptp_amount.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
                fig_ptp_amount = apply_chart_theme(fig_ptp_amount)
                fig_ptp_amount.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_ptp_amount, width='stretch')
            
            # PTP metrics
            st.subheader("📊 PTP Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            ptp_fulfilled = len(ptp_data[ptp_data['PTP Status'] == 'Fulfilled'])
            ptp_broken = len(ptp_data[ptp_data['PTP Status'] == 'Broken'])
            ptp_pending = len(ptp_data[ptp_data['PTP Status'] == 'Pending'])
            ptp_success_rate = (ptp_fulfilled / len(ptp_data) * 100) if len(ptp_data) > 0 else 0
            
            with col1:
                st.metric("✅ Fulfilled", f"{ptp_fulfilled:,}")
            with col2:
                st.metric("❌ Broken", f"{ptp_broken:,}")
            with col3:
                st.metric("⏳ Pending", f"{ptp_pending:,}")
            with col4:
                st.metric("📈 Success Rate", f"{ptp_success_rate:.1f}%")
        else:
            st.info("No PTP data available for the selected filters.")
        
        st.markdown("---")
        
        # ========== NEW SECTION 5A: PTP Date Range Analysis ==========
        st.header("📅 PTP Date Range Analysis")
        
        # PTP Date Range Filter
        st.subheader("🔍 Select PTP Date Range")
        
        # Get min and max PTP dates
        ptp_dates = filtered_df['PTP Date'].dropna()
        
        if len(ptp_dates) > 0:
            min_ptp_date = pd.to_datetime(ptp_dates).min().date()
            max_ptp_date = pd.to_datetime(ptp_dates).max().date()
            
            col1, col2 = st.columns(2)
            with col1:
                ptp_start_date = st.date_input(
                    "PTP Start Date",
                    value=min_ptp_date,
                    min_value=min_ptp_date,
                    max_value=max_ptp_date,
                    key="ptp_start"
                )
            with col2:
                ptp_end_date = st.date_input(
                    "PTP End Date",
                    value=max_ptp_date,
                    min_value=min_ptp_date,
                    max_value=max_ptp_date,
                    key="ptp_end"
                )
            
            # Filter by PTP Date Range
            ptp_range_df = filtered_df[
                (pd.to_datetime(filtered_df['PTP Date']).dt.date >= ptp_start_date) &
                (pd.to_datetime(filtered_df['PTP Date']).dt.date <= ptp_end_date) &
                (filtered_df['PTP Status'].notna()) &
                (filtered_df['PTP Amount'].notna())
            ].copy()
            
            if len(ptp_range_df) > 0:
                # Additional PTP Status Filter (Optional)
                st.subheader("🎯 Optional: Filter by PTP Status")
                ptp_status_options = ['All Status'] + sorted(ptp_range_df['PTP Status'].unique().tolist())
                selected_ptp_filter = st.selectbox("Select Specific PTP Status", ptp_status_options, key="ptp_status_filter")
                
                if selected_ptp_filter != 'All Status':
                    ptp_range_df = ptp_range_df[ptp_range_df['PTP Status'] == selected_ptp_filter]
                
                # Calculate key metrics
                total_ptp_customers = ptp_range_df['DisbursementID'].nunique()
                total_ptp_amount_range = ptp_range_df['PTP Amount'].sum()
                total_collection_from_ptp = ptp_range_df['Collection Amount'].sum()
                total_comms_ptp = ptp_range_df['Total Communications'].sum()
                
                # Customers who gave collection
                customers_with_collection = ptp_range_df[ptp_range_df['Collection Amount'] > 0]['DisbursementID'].nunique()
                collection_amount_received = ptp_range_df[ptp_range_df['Collection Amount'] > 0]['Collection Amount'].sum()
                
                # Customers who did NOT give collection
                customers_without_collection = ptp_range_df[ptp_range_df['Collection Amount'] == 0]['DisbursementID'].nunique()
                ptp_amount_no_collection = ptp_range_df[ptp_range_df['Collection Amount'] == 0]['PTP Amount'].sum()
                
                # Display Key Metrics
                st.subheader("📊 PTP Date Range Metrics")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("👥 Total PTP Customers", f"{total_ptp_customers:,}")
                with col2:
                    st.metric("💰 Total PTP Amount", f"₹{total_ptp_amount_range:,.0f}")
                with col3:
                    st.metric("💵 Collection Received", f"₹{total_collection_from_ptp:,.0f}")
                with col4:
                    st.metric("📞 Total Communications", f"{total_comms_ptp:,}")
                with col5:
                    collection_rate_ptp = (total_collection_from_ptp / total_ptp_amount_range * 100) if total_ptp_amount_range > 0 else 0
                    st.metric("📈 Collection %", f"{collection_rate_ptp:.1f}%")
                
                st.markdown("---")
                
                # Collection vs No Collection
                st.subheader("💸 Collection Status Breakdown")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ Customers Who Gave Collection")
                    st.metric("👥 Customer Count", f"{customers_with_collection:,}")
                    st.metric("💵 Collection Amount", f"₹{collection_amount_received:,.0f}")
                    
                    # Show breakdown by PTP Status
                    collection_by_status = ptp_range_df[ptp_range_df['Collection Amount'] > 0].groupby('PTP Status').agg({
                        'DisbursementID': 'nunique',
                        'Collection Amount': 'sum',
                        'PTP Amount': 'sum'
                    }).round(2)
                    collection_by_status.columns = ['Customers', 'Collection (₹)', 'PTP Amount (₹)']
                    st.dataframe(collection_by_status, width='stretch')
                
                with col2:
                    st.markdown("### ❌ Customers Who Did NOT Give Collection")
                    st.metric("👥 Customer Count", f"{customers_without_collection:,}")
                    st.metric("💰 PTP Amount (Unpaid)", f"₹{ptp_amount_no_collection:,.0f}")
                    
                    # Show breakdown by PTP Status
                    no_collection_by_status = ptp_range_df[ptp_range_df['Collection Amount'] == 0].groupby('PTP Status').agg({
                        'DisbursementID': 'nunique',
                        'PTP Amount': 'sum'
                    }).round(2)
                    no_collection_by_status.columns = ['Customers', 'PTP Amount (₹)']
                    st.dataframe(no_collection_by_status, width='stretch')
                
                # Visualization
                st.subheader("📊 Visual Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pie chart: Collection vs No Collection
                    collection_status_data = pd.DataFrame({
                        'Status': ['Collection Received', 'No Collection'],
                        'Count': [customers_with_collection, customers_without_collection]
                    })
                    
                    fig_collection_status = px.pie(
                        collection_status_data,
                        values='Count',
                        names='Status',
                        title='Customers: Collection Status',
                        color='Status',
                        color_discrete_map={'Collection Received': '#2ecc71', 'No Collection': '#e74c3c'},
                        hole=0.4
                    )
                    fig_collection_status.update_traces(textposition='inside', textinfo='percent+label+value')
                    fig_collection_status = apply_chart_theme(fig_collection_status)
                    fig_collection_status.update_layout(height=400)
                    st.plotly_chart(fig_collection_status, width='stretch')
                
                with col2:
                    # Bar chart: PTP Status wise collection
                    ptp_status_summary = ptp_range_df.groupby('PTP Status').agg({
                        'DisbursementID': 'nunique',
                        'Collection Amount': 'sum',
                        'Total Communications': 'sum'
                    }).reset_index()
                    
                    fig_ptp_status = px.bar(
                        ptp_status_summary,
                        x='PTP Status',
                        y='DisbursementID',
                        title='Customers by PTP Status',
                        labels={'DisbursementID': 'Number of Customers', 'PTP Status': 'PTP Status'},
                        color='Collection Amount',
                        color_continuous_scale='Viridis',
                        text='DisbursementID'
                    )
                    fig_ptp_status.update_traces(texttemplate='%{text:,}', textposition='outside')
                    fig_ptp_status = apply_chart_theme(fig_ptp_status)
                    fig_ptp_status.update_layout(height=400)
                    st.plotly_chart(fig_ptp_status, width='stretch')
                
                # Detailed Table
                st.subheader("📋 Detailed Customer List")
                
                # Determine which Customer Name column exists
                customer_name_col = 'CustomerName' if 'CustomerName' in ptp_range_df.columns else 'Customer Name'
                
                # Prepare detailed data
                detailed_data = ptp_range_df.groupby('DisbursementID').agg({
                    customer_name_col: 'first',
                    'Branch': 'first',
                    'PTP Date': 'first',
                    'PTP Status': 'first',
                    'PTP Amount': 'sum',
                    'Collection Amount': 'sum',
                    'Total Communications': 'sum'
                }).reset_index()
                
                detailed_data.columns = ['Disbursement ID', 'Customer Name', 'Branch', 'PTP Date', 
                                        'PTP Status', 'PTP Amount (₹)', 'Collection Amount (₹)', 
                                        'Total Communications']
                
                detailed_data['Collection Status'] = detailed_data['Collection Amount (₹)'].apply(
                    lambda x: '✅ Collected' if x > 0 else '❌ Not Collected'
                )
                
                # Format amounts
                detailed_data['PTP Amount (₹)'] = detailed_data['PTP Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
                detailed_data['Collection Amount (₹)'] = detailed_data['Collection Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
                
                st.dataframe(detailed_data, width='stretch', height=400)
                
                # Download button for this analysis
                detailed_csv = detailed_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download PTP Date Range Analysis (CSV)",
                    data=detailed_csv,
                    file_name=f'ptp_analysis_{ptp_start_date}_to_{ptp_end_date}.csv',
                    mime='text/csv',
                )
            else:
                st.warning(f"No PTP records found between {ptp_start_date} and {ptp_end_date}")
        else:
            st.info("No PTP Date data available in the filtered dataset.")
        
        st.markdown("---")
        
        # ========== NEW SECTION 5B: Collections WITHOUT PTP ==========
        st.header("💰 Collections Without PTP Analysis")
        st.markdown("**Customers who gave collection WITHOUT giving PTP Status/Amount**")
        
        # Date range for collection (using PTP Date range selected above)
        if len(ptp_dates) > 0:
            st.subheader("📅 Using Same Date Range as Above")
            st.info(f"Analyzing collections from {ptp_start_date} to {ptp_end_date}")
            
            # Filter: Collections > 0 BUT No PTP Status or No PTP Amount
            collections_without_ptp = filtered_df[
                (filtered_df['Collection Amount'] > 0) &
                (
                    
                    (filtered_df['PTP Amount']==0)
                )
            ].copy()
            
            # Further filter by date range if Collection Date is available
            if 'Collection Date' in collections_without_ptp.columns:
                collections_without_ptp = collections_without_ptp[
                    (pd.to_datetime(collections_without_ptp['Collection Date'], errors='coerce').dt.date >= ptp_start_date) &
                    (pd.to_datetime(collections_without_ptp['Collection Date'], errors='coerce').dt.date <= ptp_end_date)
                ]
            
            if len(collections_without_ptp) > 0:
                # Calculate metrics
                customers_no_ptp = collections_without_ptp['DisbursementID'].nunique()
                total_collection_no_ptp = collections_without_ptp['Collection Amount'].sum()
                total_comms_no_ptp = collections_without_ptp['Total Communications'].sum()
                avg_collection_no_ptp = collections_without_ptp.groupby('DisbursementID')['Collection Amount'].sum().mean()
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("👥 Customers", f"{customers_no_ptp:,}")
                with col2:
                    st.metric("💵 Total Collection", f"₹{total_collection_no_ptp:,.0f}")
                with col3:
                    st.metric("📞 Communications", f"{total_comms_no_ptp:,}")
                with col4:
                    st.metric("📊 Avg per Customer", f"₹{avg_collection_no_ptp:,.0f}")
                
                st.markdown("---")
                
                # Branch-wise breakdown
                st.subheader("🏢 Branch-wise Collections Without PTP")
                
                branch_no_ptp = collections_without_ptp.groupby('Branch').agg({
                    'DisbursementID': 'nunique',
                    'Collection Amount': 'sum',
                    'Total Communications': 'sum'
                }).sort_values('Collection Amount', ascending=False).head(10)
                
                branch_no_ptp.columns = ['Customers', 'Collection Amount (₹)', 'Communications']
                
                fig_branch_no_ptp = px.bar(
                    branch_no_ptp.reset_index(),
                    x='Branch',
                    y='Collection Amount (₹)',
                    title='Top 10 Branches - Collections Without PTP',
                    color='Collection Amount (₹)',
                    color_continuous_scale='Blues',
                    text='Collection Amount (₹)'
                )
                fig_branch_no_ptp.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
                fig_branch_no_ptp = apply_chart_theme(fig_branch_no_ptp)
                fig_branch_no_ptp.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig_branch_no_ptp, width='stretch')
                
                # Detailed table
                st.subheader("📋 Customer Details - Collections Without PTP")
                
                # Determine which Customer Name column exists
                customer_name_col = 'CustomerName' if 'CustomerName' in collections_without_ptp.columns else 'Customer Name'
                
                no_ptp_details = collections_without_ptp.groupby('DisbursementID').agg({
                    customer_name_col: 'first',
                    'Branch': 'first',
                    'Collection Amount': 'sum',
                    'Total Communications': 'sum',
                    'PTP Status': 'first',
                    'PTP Amount': 'first'
                }).reset_index()
                
                no_ptp_details.columns = ['Disbursement ID', 'Customer Name', 'Branch', 
                                         'Collection Amount (₹)', 'Communications', 
                                         'PTP Status', 'PTP Amount']
                
                no_ptp_details['Collection Amount (₹)'] = no_ptp_details['Collection Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
                no_ptp_details['PTP Status'] = no_ptp_details['PTP Status'].fillna('No PTP')
                no_ptp_details['PTP Amount'] = no_ptp_details['PTP Amount'].fillna(0).apply(lambda x: f"₹{x:,.2f}" if x > 0 else 'No PTP')
                
                st.dataframe(no_ptp_details, width='stretch', height=400)
                
                # Download button
                no_ptp_csv = no_ptp_details.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Collections Without PTP (CSV)",
                    data=no_ptp_csv,
                    file_name=f'collections_without_ptp_{ptp_start_date}_to_{ptp_end_date}.csv',
                    mime='text/csv',
                )
            else:
                st.info(f"No collections without PTP found in the date range {ptp_start_date} to {ptp_end_date}")
        else:
            st.info("No PTP Date data available for analysis.")
        
        st.markdown("---")
        
        # Section 6: Branch Performance
        st.header("🏢 Branch Performance Analysis")
        
        branch_performance = filtered_df.groupby('Branch').agg({
            'Collection Amount': 'sum',
            'Overdue Amount': 'sum',
            'DisbursementID': 'nunique',
            'Total Communications': 'sum'
        }).round(2)
        
        branch_performance['Collection Rate (%)'] = (
            branch_performance['Collection Amount'] / branch_performance['Overdue Amount'] * 100
        ).round(2)
        branch_performance = branch_performance.sort_values('Collection Amount', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 5 Performing Branches")
            top_5 = branch_performance.head(5)
            fig_top = px.bar(
                x=top_5.index,
                y=top_5['Collection Amount'],
                title='Top 5 Branches by Collection Amount',
                labels={'x': 'Branch', 'y': 'Collection Amount (₹)'},
                color=top_5['Collection Amount'],
                color_continuous_scale='Greens',
                text=top_5['Collection Amount']
            )
            fig_top.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_top = apply_chart_theme(fig_top)
            fig_top.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_top, width='stretch')
        
        with col2:
            st.subheader("⚠️ Bottom 5 Branches Needing Attention")
            bottom_5 = branch_performance[branch_performance['Collection Amount'] > 0].tail(5)
            fig_bottom = px.bar(
                x=bottom_5.index,
                y=bottom_5['Collection Amount'],
                title='Bottom 5 Branches by Collection Amount',
                labels={'x': 'Branch', 'y': 'Collection Amount (₹)'},
                color=bottom_5['Collection Amount'],
                color_continuous_scale='Reds',
                text=bottom_5['Collection Amount']
            )
            fig_bottom.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_bottom = apply_chart_theme(fig_bottom)
            fig_bottom.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_bottom, width='stretch')
        
        # Branch performance table
        st.subheader("📋 Complete Branch Performance Table")
        branch_display = branch_performance.copy()
        branch_display['Collection Amount'] = branch_display['Collection Amount'].apply(lambda x: f"₹{x:,.2f}")
        branch_display['Overdue Amount'] = branch_display['Overdue Amount'].apply(lambda x: f"₹{x:,.2f}")
        branch_display.columns = ['Collection (₹)', 'Overdue (₹)', 'Unique Customers', 'Communications', 'Collection Rate (%)']
        st.dataframe(branch_display, width='stretch', height=400)
        
        st.markdown("---")
        
        # Section 7: DPD Analysis
        st.header("⏰ Days Past Due (DPD) Analysis")
        
        # Create DPD buckets
        def dpd_bucket(days):
            if days == 0:
                return '0 Days (Current)'
            elif days <= 30:
                return '1-30 Days'
            elif days <= 60:
                return '31-60 Days'
            elif days <= 90:
                return '61-90 Days'
            elif days <= 180:
                return '91-180 Days'
            else:
                return '180+ Days'
        
        filtered_df['DPD_Bucket'] = filtered_df['NumberOfDaysPastDue'].apply(dpd_bucket)
        
        col1, col2 = st.columns(2)
        
        with col1:
            dpd_count = filtered_df['DPD_Bucket'].value_counts()
            bucket_order = ['0 Days (Current)', '1-30 Days', '31-60 Days', '61-90 Days', '91-180 Days', '180+ Days']
            dpd_count = dpd_count.reindex(bucket_order, fill_value=0)
            
            fig_dpd = px.bar(
                x=dpd_count.index,
                y=dpd_count.values,
                title='Loan Distribution by DPD Bucket',
                labels={'x': 'DPD Bucket', 'y': 'Number of Loans'},
                color=dpd_count.values,
                color_continuous_scale='RdYlGn_r',
                text=dpd_count.values
            )
            fig_dpd.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_dpd = apply_chart_theme(fig_dpd)
            fig_dpd.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_dpd, width='stretch')
        
        with col2:
            dpd_amount = filtered_df.groupby('DPD_Bucket')['Overdue Amount'].sum()
            dpd_amount = dpd_amount.reindex(bucket_order, fill_value=0)
            
            fig_dpd_amount = px.pie(
                values=dpd_amount.values,
                names=dpd_amount.index,
                title='Overdue Amount by DPD Bucket',
                color_discrete_sequence=px.colors.sequential.RdBu_r,
                hole=0.3
            )
            fig_dpd_amount.update_traces(textposition='inside', textinfo='percent+label')
            fig_dpd_amount = apply_chart_theme(fig_dpd_amount)
            fig_dpd_amount.update_layout(height=400)
            st.plotly_chart(fig_dpd_amount, width='stretch')
        
        st.markdown("---")
        
        # Section 8: Active vs Inactive Loans
        st.header("📊 Loan Portfolio Status")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        active_count = len(filtered_df[filtered_df['IsActive'] == True])
        inactive_count = len(filtered_df[filtered_df['IsActive'] == False])
        
        with col1:
            st.metric("✅ Active Loans", f"{active_count:,}")
        
        with col2:
            st.metric("❌ Inactive Loans", f"{inactive_count:,}")
        
        with col3:
            active_percentage = (active_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.metric("📈 Active Rate", f"{active_percentage:.1f}%")
        
        # Visualization
        loan_status_data = pd.DataFrame({
            'Status': ['Active', 'Inactive'],
            'Count': [active_count, inactive_count]
        })
        
        fig_status = px.pie(
            loan_status_data,
            values='Count',
            names='Status',
            title='Active vs Inactive Loans Distribution',
            color='Status',
            color_discrete_map={'Active': '#2ecc71', 'Inactive': '#e74c3c'},
            hole=0.4
        )
        fig_status.update_traces(textposition='inside', textinfo='percent+label+value')
        fig_status = apply_chart_theme(fig_status)
        fig_status.update_layout(height=400)
        st.plotly_chart(fig_status, width='stretch')
        
        st.markdown("---")
        
        # Section 9: Trend Analysis
        st.header("📈 Trend Analysis Over Time")
        
        daily_trends = filtered_df.groupby('Date').agg({
            'Collection Amount': 'sum',
            'Total Communications': 'sum',
            'Overdue Amount': 'sum'
        }).reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_collection_trend = px.line(
                daily_trends,
                x='Date',
                y='Collection Amount',
                title='Daily Collection Trend',
                labels={'Collection Amount': 'Collection Amount (₹)'},
                markers=True
            )
            fig_collection_trend.update_traces(line_color='#2ecc71', line_width=2)
            fig_collection_trend = apply_chart_theme(fig_collection_trend)
            fig_collection_trend.update_layout(height=400)
            st.plotly_chart(fig_collection_trend, width='stretch')
        
        with col2:
            fig_comm_trend = px.line(
                daily_trends,
                x='Date',
                y='Total Communications',
                title='Daily Communication Volume',
                labels={'Total Communications': 'Communications Sent'},
                markers=True
            )
            fig_comm_trend.update_traces(line_color='#3498db', line_width=2)
            fig_comm_trend = apply_chart_theme(fig_comm_trend)
            fig_comm_trend.update_layout(height=400)
            st.plotly_chart(fig_comm_trend, width='stretch')
        
        st.markdown("---")
        
        # Section 10: Summary Report
        st.header("📄 Executive Summary Report")
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.subheader("💼 Portfolio Overview")
            st.write(f"**Total Unique Customers:** {total_unique_customers:,}")
            st.write(f"**Active Loans:** {active_count:,}")
            st.write(f"**Inactive Loans:** {inactive_count:,}")
            st.write(f"**Total Branches:** {filtered_df['Branch'].nunique()}")
            
            st.subheader("💰 Financial Metrics")
            st.write(f"**Total Overdue Amount:** ₹{total_overdue_amount:,.2f}")
            st.write(f"**Total Collection Amount:** ₹{total_collection_amount:,.2f}")
            st.write(f"**Collection Rate:** {collection_rate:.2f}%")
            st.write(f"**Total PTP Amount:** ₹{total_ptp_amount:,.2f}")
        
        with summary_col2:
            st.subheader("📞 Communication Summary")
            st.write(f"**Total Communications:** {total_communications:,}")
            st.write(f"**WhatsApp Messages:** {total_whatsapp_sent:,}")
            st.write(f"**Blaster Calls:** {total_blaster_sent:,}")
            st.write(f"**AI Calls:** {total_AI_Calls_sent:,}")
            
            st.subheader("🎯 PTP Summary")
            if len(ptp_data) > 0:
                st.write(f"**Total PTPs:** {len(ptp_data):,}")
                st.write(f"**Fulfilled:** {ptp_fulfilled:,}")
                st.write(f"**Broken:** {ptp_broken:,}")
                st.write(f"**Success Rate:** {ptp_success_rate:.1f}%")
            else:
                st.write("No PTP data available")
        
        st.markdown("---")
        
        # Section 11: Download Reports
        st.header("📥 Download Reports")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Download Filtered Data (CSV)",
                data=csv,
                file_name=f'filtered_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
            )
        
        with col2:
            branch_csv = branch_performance.to_csv().encode('utf-8')
            st.download_button(
                label="🏢 Download Branch Performance (CSV)",
                data=branch_csv,
                file_name=f'branch_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
            )
        
        with col3:
            if len(collection_data) > 0:
                collection_csv = collection_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="💰 Download Collection Data (CSV)",
                    data=collection_csv,
                    file_name=f'collection_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                )
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
        <div style='text-align: center; color: #000000; padding: 20px;'>
            <p style='color: #000000;'><strong>Loan Collection Analytics Dashboard</strong></p>
            <p style='color: #666666;'>Powered by Streamlit | Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    """, unsafe_allow_html=True)

except FileNotFoundError:
    st.error("⚠️ Error: 'Vinayna_Latest.csv' file not found. Please make sure the file is in the same directory as this script.")
    st.info("📁 Place your 'Vinayna_Latest.csv' file in the same folder and refresh the page.")
except Exception as e:
    st.error(f"⚠️ An error occurred: {str(e)}")
    st.info("Please check your data file and try again.")

# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# from datetime import datetime
# import numpy as np

# # Page configuration
# st.set_page_config(
#     page_title="Loan Collection Analytics Dashboard",
#     page_icon="📊",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Force light/white theme with black text
# st.markdown("""
#     <style>
#     /* Fix metric boxes - make values visible */
#     [data-testid="stMetricValue"] {
#         color: #FFFFFF !important;
#         font-weight: 700;
#         font-size: 28px !important;
#     }
    
#     [data-testid="stMetricLabel"] {
#         color: #CCCCCC !important;
#         font-weight: 600;
#         font-size: 14px !important;
#     }
    
#     /* Make metric containers have dark background */
#     [data-testid="stMetric"] {
#         background-color: #1E1E1E;
#         padding: 20px;
#         border-radius: 10px;
#         box-shadow: 0 2px 8px rgba(0,0,0,0.3);
#     }
    
#     /* Sidebar text visibility */
#     [data-testid="stSidebar"] * {
#         color: inherit;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # Helper function to apply dark theme to all charts
# def apply_chart_theme(fig):
#     fig.update_layout(
#         plot_bgcolor='rgba(0,0,0,0)',  # Transparent
#         paper_bgcolor='rgba(0,0,0,0)',  # Transparent
#         font=dict(color='white', size=12),
#         title_font=dict(color='white', size=16, family='Arial', weight='bold'),
#         xaxis=dict(gridcolor='#444444', color='white'),
#         yaxis=dict(gridcolor='#444444', color='white'),
#         legend=dict(font=dict(color='white'))
#     )
#     return fig

# # Load data with caching
# @st.cache_data
# def load_data():
#     df = pd.read_csv('Vinayna_Latest.csv')
#     df['Date'] = pd.to_datetime(df['Date'])
#     return df


# # Main title
# st.title("📊 Loan Collection Analytics Dashboard")
# st.markdown("---")

# # Load data
# try:
#     df = load_data()
    
#     # Sidebar filters
#     st.sidebar.header("🔍 Filters")
    
#     # Date filter
#     min_date = df['Date'].min().date()
#     max_date = df['Date'].max().date()
    
#     date_range = st.sidebar.date_input(
#         "Select Date Range",
#         value=(min_date, max_date),
#         min_value=min_date,
#         max_value=max_date
#     )
    
#     # Branch filter
#     branches = ['All Branches'] + sorted(df['Branch'].dropna().unique().tolist())
#     selected_branch = st.sidebar.selectbox("Select Branch", branches)
    
#     # PTP Status filter
#     ptp_statuses = ['All Status'] + sorted(df['PTP Status'].dropna().unique().tolist())
#     selected_ptp_status = st.sidebar.selectbox("Select PTP Status", ptp_statuses)
    
#     # Loan Status filter
#     loan_status = st.sidebar.radio("Loan Status", ['All', 'Active Only', 'Inactive Only'])
    
#     # Apply filters
#     filtered_df = df.copy()
    
#     # Date filter
#     if len(date_range) == 2:
#         start_date, end_date = date_range
#         filtered_df = filtered_df[(filtered_df['Date'].dt.date >= start_date) & 
#                                   (filtered_df['Date'].dt.date <= end_date)]
    
#     # Branch filter
#     if selected_branch != 'All Branches':
#         filtered_df = filtered_df[filtered_df['Branch'] == selected_branch]
    
#     # PTP Status filter
#     if selected_ptp_status != 'All Status':
#         filtered_df = filtered_df[filtered_df['PTP Status'] == selected_ptp_status]
    
#     # Loan Status filter
#     if loan_status == 'Active Only':
#         filtered_df = filtered_df[filtered_df['IsActive'] == True]
#     elif loan_status == 'Inactive Only':
#         filtered_df = filtered_df[filtered_df['IsActive'] == False]
    
#     # Display filter info
#     st.sidebar.markdown("---")
#     st.sidebar.info(f"📅 Showing data from {filtered_df['Date'].min().date()} to {filtered_df['Date'].max().date()}")
#     st.sidebar.info(f"📊 Total Records: {len(filtered_df):,}")
    
#     # Calculate metrics
#     total_unique_customers = filtered_df['DisbursementID'].nunique()
#     total_communications = filtered_df['Total Communications'].sum()
#     total_whatsapp_sent = filtered_df['WhatsApp'].sum()
#     total_blaster_sent = filtered_df['Blaster'].sum()
#     total_AI_Calls_sent = filtered_df['AI Calls'].sum()
#     total_ptp_amount = filtered_df['PTP Amount'].sum()
#     total_collection_amount = filtered_df['Collection Amount'].sum()
#     total_overdue_amount = filtered_df['Overdue Amount'].sum()
#     collection_rate = (total_collection_amount / total_overdue_amount * 100) if total_overdue_amount > 0 else 0
    
#     # Section 1: Key Performance Indicators
#     st.header("📈 Key Performance Indicators")
    
#     col1, col2, col3, col4, col5 = st.columns(5)
    
#     with col1:
#         st.metric(
#             label="👥 Unique Customers",
#             value=f"{total_unique_customers:,}",
#             delta=None
#         )
    
#     with col2:
#         st.metric(
#             label="📞 Total Communications",
#             value=f"{total_communications:,}",
#             delta=None
#         )
    
#     with col3:
#         st.metric(
#             label="💰 PTP Amount",
#             value=f"₹{total_ptp_amount:,.0f}",
#             delta=None
#         )
    
#     with col4:
#         st.metric(
#             label="💵 Collection Amount",
#             value=f"₹{total_collection_amount:,.0f}",
#             delta=None
#         )
    
#     with col5:
#         st.metric(
#             label="📊 Collection Rate",
#             value=f"{collection_rate:.2f}%",
#             delta=None
#         )
    
#     st.markdown("---")
    
#     # Section 2: Communication Breakdown
#     st.header("📱 Communication Channel Breakdown")
    
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.metric(
#             label="📱 WhatsApp Sent",
#             value=f"{total_whatsapp_sent:,}",
#             delta=None
#         )
    
#     with col2:
#         st.metric(
#             label="📢 Blaster Sent",
#             value=f"{total_blaster_sent:,}",
#             delta=None
#         )
    
#     with col3:
#         st.metric(
#             label="🤖 AI Calls Sent",
#             value=f"{total_AI_Calls_sent:,}",
#             delta=None
#         )
    
#     st.markdown("---")
    
#     # Section 3: Collection Analysis by PTP Source
#     st.header("💰 Collection Amount by PTP Source")
    
#     collection_data = filtered_df[(filtered_df['Collection Amount'] > 0) & 
#                                   (filtered_df['PTP Source'].notna())].copy()
    
#     if len(collection_data) > 0:
#         collection_by_source = collection_data.groupby('PTP Source')['Collection Amount'].sum().sort_values(ascending=False)
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             # Bar chart
#             fig_bar = px.bar(
#                 x=collection_by_source.index,
#                 y=collection_by_source.values,
#                 labels={'x': 'PTP Source', 'y': 'Collection Amount (₹)'},
#                 title='Collection Amount by PTP Source',
#                 color=collection_by_source.values,
#                 color_continuous_scale='Blues',
#                 text=collection_by_source.values
#             )
#             fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
#             fig_bar = apply_chart_theme(fig_bar)
#             fig_bar.update_layout(showlegend=False, height=400)
#             st.plotly_chart(fig_bar, width='stretch')
        
#         with col2:
#             # Pie chart
#             fig_pie = px.pie(
#                 values=collection_by_source.values,
#                 names=collection_by_source.index,
#                 title='Collection Distribution by PTP Source',
#                 hole=0.4,
#                 color_discrete_sequence=px.colors.qualitative.Set3
#             )
#             fig_pie.update_traces(textposition='inside', textinfo='percent+label')
#             fig_pie = apply_chart_theme(fig_pie)
#             fig_pie.update_layout(height=400)
#             st.plotly_chart(fig_pie, width='stretch')
        
#         # Detailed breakdown
#         st.subheader("📋 Detailed Collection Breakdown")
#         collection_count = collection_data.groupby('PTP Source').agg({
#             'Collection Amount': ['count', 'sum', 'mean']
#         }).round(2)
#         collection_count.columns = ['Number of Collections', 'Total Amount (₹)', 'Average Amount (₹)']
#         collection_count = collection_count.sort_values('Total Amount (₹)', ascending=False)
#         collection_count['Total Amount (₹)'] = collection_count['Total Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
#         collection_count['Average Amount (₹)'] = collection_count['Average Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
#         st.dataframe(collection_count, width='stretch')
#     else:
#         st.warning("No collection data available for the selected filters.")
    
#     st.markdown("---")
    
#     # Section 4: Communication Channel Effectiveness
#     st.header("📊 Communication Channel Effectiveness")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         # Communication volume comparison
#         comm_data = pd.DataFrame({
#             'Channel': ['WhatsApp', 'Blaster', 'AI Calls'],
#             'Count': [total_whatsapp_sent, total_blaster_sent, total_AI_Calls_sent]
#         })
        
#         fig_comm = px.bar(
#             comm_data,
#             x='Channel',
#             y='Count',
#             title='Communication Volume by Channel',
#             color='Count',
#             color_continuous_scale='Viridis',
#             text='Count'
#         )
#         fig_comm.update_traces(texttemplate='%{text:,}', textposition='outside')
#         fig_comm = apply_chart_theme(fig_comm)
#         fig_comm.update_layout(showlegend=False, height=400)
#         st.plotly_chart(fig_comm, width='stretch')
    
#     with col2:
#         # Collection by communication channel
#         if len(collection_data) > 0:
#             fig_comm_collect = px.scatter(
#                 collection_data.groupby('PTP Source').agg({
#                     'Collection Amount': 'sum',
#                     'DisbursementID': 'count'
#                 }).reset_index(),
#                 x='DisbursementID',
#                 y='Collection Amount',
#                 size='Collection Amount',
#                 color='PTP Source',
#                 title='Collections vs Number of Transactions',
#                 labels={'DisbursementID': 'Number of Transactions', 'Collection Amount': 'Total Collection (₹)'},
#                 color_discrete_sequence=px.colors.qualitative.Set2
#             )
#             fig_comm_collect = apply_chart_theme(fig_comm_collect)
#             fig_comm_collect.update_layout(height=400)
#             st.plotly_chart(fig_comm_collect, width='stretch')
    
#     st.markdown("---")
    
#     # Section 5: PTP Status Breakdown
#     st.header("🎯 PTP (Promise to Pay) Status Analysis")
    
#     ptp_data = filtered_df[filtered_df['PTP Status'].notna()]
    
#     if len(ptp_data) > 0:
#         col1, col2 = st.columns(2)
        
#         with col1:
#             ptp_status_count = ptp_data['PTP Status'].value_counts()
#             fig_ptp = px.pie(
#                 values=ptp_status_count.values,
#                 names=ptp_status_count.index,
#                 title='PTP Status Distribution',
#                 color_discrete_sequence=px.colors.qualitative.Pastel,
#                 hole=0.3
#             )
#             fig_ptp.update_traces(textposition='inside', textinfo='percent+label+value')
#             fig_ptp = apply_chart_theme(fig_ptp)
#             fig_ptp.update_layout(height=400)
#             st.plotly_chart(fig_ptp, width='stretch')
        
#         with col2:
#             ptp_amount_by_status = ptp_data.groupby('PTP Status')['PTP Amount'].sum().sort_values(ascending=False)
#             fig_ptp_amount = px.bar(
#                 x=ptp_amount_by_status.index,
#                 y=ptp_amount_by_status.values,
#                 title='PTP Amount by Status',
#                 labels={'x': 'PTP Status', 'y': 'PTP Amount (₹)'},
#                 color=ptp_amount_by_status.values,
#                 color_continuous_scale='Oranges',
#                 text=ptp_amount_by_status.values
#             )
#             fig_ptp_amount.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
#             fig_ptp_amount = apply_chart_theme(fig_ptp_amount)
#             fig_ptp_amount.update_layout(showlegend=False, height=400)
#             st.plotly_chart(fig_ptp_amount, width='stretch')
        
#         # PTP metrics
#         st.subheader("📊 PTP Metrics")
#         col1, col2, col3, col4 = st.columns(4)
        
#         ptp_fulfilled = len(ptp_data[ptp_data['PTP Status'] == 'Fulfilled'])
#         ptp_broken = len(ptp_data[ptp_data['PTP Status'] == 'Broken'])
#         ptp_pending = len(ptp_data[ptp_data['PTP Status'] == 'Pending'])
#         ptp_success_rate = (ptp_fulfilled / len(ptp_data) * 100) if len(ptp_data) > 0 else 0
        
#         with col1:
#             st.metric("✅ Fulfilled", f"{ptp_fulfilled:,}")
#         with col2:
#             st.metric("❌ Broken", f"{ptp_broken:,}")
#         with col3:
#             st.metric("⏳ Pending", f"{ptp_pending:,}")
#         with col4:
#             st.metric("📈 Success Rate", f"{ptp_success_rate:.1f}%")
#     else:
#         st.info("No PTP data available for the selected filters.")
    
#     st.markdown("---")
    
#     # ========== NEW SECTION 5A: PTP Date Range Analysis ==========
#     st.header("📅 PTP Date Range Analysis")
    
#     # PTP Date Range Filter
#     st.subheader("🔍 Select PTP Date Range")
    
#     # Get min and max PTP dates
#     ptp_dates = filtered_df['PTP Date'].dropna()
    
#     if len(ptp_dates) > 0:
#         min_ptp_date = pd.to_datetime(ptp_dates).min().date()
#         max_ptp_date = pd.to_datetime(ptp_dates).max().date()
        
#         col1, col2 = st.columns(2)
#         with col1:
#             ptp_start_date = st.date_input(
#                 "PTP Start Date",
#                 value=min_ptp_date,
#                 min_value=min_ptp_date,
#                 max_value=max_ptp_date,
#                 key="ptp_start"
#             )
#         with col2:
#             ptp_end_date = st.date_input(
#                 "PTP End Date",
#                 value=max_ptp_date,
#                 min_value=min_ptp_date,
#                 max_value=max_ptp_date,
#                 key="ptp_end"
#             )
        
#         # Filter by PTP Date Range
#         ptp_range_df = filtered_df[
#             (pd.to_datetime(filtered_df['PTP Date']).dt.date >= ptp_start_date) &
#             (pd.to_datetime(filtered_df['PTP Date']).dt.date <= ptp_end_date) &
#             (filtered_df['PTP Status'].notna()) &
#             (filtered_df['PTP Amount'].notna())
#         ].copy()
        
#         if len(ptp_range_df) > 0:
#             # Additional PTP Status Filter (Optional)
#             st.subheader("🎯 Optional: Filter by PTP Status")
#             ptp_status_options = ['All Status'] + sorted(ptp_range_df['PTP Status'].unique().tolist())
#             selected_ptp_filter = st.selectbox("Select Specific PTP Status", ptp_status_options, key="ptp_status_filter")
            
#             if selected_ptp_filter != 'All Status':
#                 ptp_range_df = ptp_range_df[ptp_range_df['PTP Status'] == selected_ptp_filter]
            
#             # Calculate key metrics
#             total_ptp_customers = ptp_range_df['DisbursementID'].nunique()
#             total_ptp_amount_range = ptp_range_df['PTP Amount'].sum()
#             total_collection_from_ptp = ptp_range_df['Collection Amount'].sum()
#             total_comms_ptp = ptp_range_df['Total Communications'].sum()
            
#             # Customers who gave collection
#             customers_with_collection = ptp_range_df[ptp_range_df['Collection Amount'] > 0]['DisbursementID'].nunique()
#             collection_amount_received = ptp_range_df[ptp_range_df['Collection Amount'] > 0]['Collection Amount'].sum()
            
#             # Customers who did NOT give collection
#             customers_without_collection = ptp_range_df[ptp_range_df['Collection Amount'] == 0]['DisbursementID'].nunique()
#             ptp_amount_no_collection = ptp_range_df[ptp_range_df['Collection Amount'] == 0]['PTP Amount'].sum()
            
#             # Display Key Metrics
#             st.subheader("📊 PTP Date Range Metrics")
#             col1, col2, col3, col4, col5 = st.columns(5)
            
#             with col1:
#                 st.metric("👥 Total PTP Customers", f"{total_ptp_customers:,}")
#             with col2:
#                 st.metric("💰 Total PTP Amount", f"₹{total_ptp_amount_range:,.0f}")
#             with col3:
#                 st.metric("💵 Collection Received", f"₹{total_collection_from_ptp:,.0f}")
#             with col4:
#                 st.metric("📞 Total Communications", f"{total_comms_ptp:,}")
#             with col5:
#                 collection_rate_ptp = (total_collection_from_ptp / total_ptp_amount_range * 100) if total_ptp_amount_range > 0 else 0
#                 st.metric("📈 Collection %", f"{collection_rate_ptp:.1f}%")
            
#             st.markdown("---")
            
#             # Collection vs No Collection
#             st.subheader("💸 Collection Status Breakdown")
            
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 st.markdown("### ✅ Customers Who Gave Collection")
#                 st.metric("👥 Customer Count", f"{customers_with_collection:,}")
#                 st.metric("💵 Collection Amount", f"₹{collection_amount_received:,.0f}")
                
#                 # Show breakdown by PTP Status
#                 collection_by_status = ptp_range_df[ptp_range_df['Collection Amount'] > 0].groupby('PTP Status').agg({
#                     'DisbursementID': 'nunique',
#                     'Collection Amount': 'sum',
#                     'PTP Amount': 'sum'
#                 }).round(2)
#                 collection_by_status.columns = ['Customers', 'Collection (₹)', 'PTP Amount (₹)']
#                 st.dataframe(collection_by_status, width='stretch')
            
#             with col2:
#                 st.markdown("### ❌ Customers Who Did NOT Give Collection")
#                 st.metric("👥 Customer Count", f"{customers_without_collection:,}")
#                 st.metric("💰 PTP Amount (Unpaid)", f"₹{ptp_amount_no_collection:,.0f}")
                
#                 # Show breakdown by PTP Status
#                 no_collection_by_status = ptp_range_df[ptp_range_df['Collection Amount'] == 0].groupby('PTP Status').agg({
#                     'DisbursementID': 'nunique',
#                     'PTP Amount': 'sum'
#                 }).round(2)
#                 no_collection_by_status.columns = ['Customers', 'PTP Amount (₹)']
#                 st.dataframe(no_collection_by_status, width='stretch')
            
#             # Visualization
#             st.subheader("📊 Visual Analysis")
            
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 # Pie chart: Collection vs No Collection
#                 collection_status_data = pd.DataFrame({
#                     'Status': ['Collection Received', 'No Collection'],
#                     'Count': [customers_with_collection, customers_without_collection]
#                 })
                
#                 fig_collection_status = px.pie(
#                     collection_status_data,
#                     values='Count',
#                     names='Status',
#                     title='Customers: Collection Status',
#                     color='Status',
#                     color_discrete_map={'Collection Received': '#2ecc71', 'No Collection': '#e74c3c'},
#                     hole=0.4
#                 )
#                 fig_collection_status.update_traces(textposition='inside', textinfo='percent+label+value')
#                 fig_collection_status = apply_chart_theme(fig_collection_status)
#                 fig_collection_status.update_layout(height=400)
#                 st.plotly_chart(fig_collection_status, width='stretch')
            
#             with col2:
#                 # Bar chart: PTP Status wise collection
#                 ptp_status_summary = ptp_range_df.groupby('PTP Status').agg({
#                     'DisbursementID': 'nunique',
#                     'Collection Amount': 'sum',
#                     'Total Communications': 'sum'
#                 }).reset_index()
                
#                 fig_ptp_status = px.bar(
#                     ptp_status_summary,
#                     x='PTP Status',
#                     y='DisbursementID',
#                     title='Customers by PTP Status',
#                     labels={'DisbursementID': 'Number of Customers', 'PTP Status': 'PTP Status'},
#                     color='Collection Amount',
#                     color_continuous_scale='Viridis',
#                     text='DisbursementID'
#                 )
#                 fig_ptp_status.update_traces(texttemplate='%{text:,}', textposition='outside')
#                 fig_ptp_status = apply_chart_theme(fig_ptp_status)
#                 fig_ptp_status.update_layout(height=400)
#                 st.plotly_chart(fig_ptp_status, width='stretch')
            
#             # Detailed Table
#             st.subheader("📋 Detailed Customer List")
            
#             # Prepare detailed data
#             detailed_data = ptp_range_df.groupby('DisbursementID').agg({
#                 'CustomerName': 'first',
#                 'Branch': 'first',
#                 'PTP Date': 'first',
#                 'PTP Status': 'first',
#                 'PTP Amount': 'sum',
#                 'Collection Amount': 'sum',
#                 'Total Communications': 'sum'
#             }).reset_index()
            
#             detailed_data.columns = ['Disbursement ID', 'Customer Name', 'Branch', 'PTP Date', 
#                                     'PTP Status', 'PTP Amount (₹)', 'Collection Amount (₹)', 
#                                     'Total Communications']
            
#             detailed_data['Collection Status'] = detailed_data['Collection Amount (₹)'].apply(
#                 lambda x: '✅ Collected' if x > 0 else '❌ Not Collected'
#             )
            
#             # Format amounts
#             detailed_data['PTP Amount (₹)'] = detailed_data['PTP Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
#             detailed_data['Collection Amount (₹)'] = detailed_data['Collection Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
            
#             st.dataframe(detailed_data, width='stretch', height=400)
            
#             # Download button for this analysis
#             detailed_csv = detailed_data.to_csv(index=False).encode('utf-8')
#             st.download_button(
#                 label="📥 Download PTP Date Range Analysis (CSV)",
#                 data=detailed_csv,
#                 file_name=f'ptp_analysis_{ptp_start_date}_to_{ptp_end_date}.csv',
#                 mime='text/csv',
#             )
#         else:
#             st.warning(f"No PTP records found between {ptp_start_date} and {ptp_end_date}")
#     else:
#         st.info("No PTP Date data available in the filtered dataset.")
    
#     st.markdown("---")
    
#     # ========== NEW SECTION 5B: Collections WITHOUT PTP ==========
#     st.header("💰 Collections Without PTP Analysis")
#     st.markdown("**Customers who gave collection WITHOUT giving PTP Status/Amount**")
    
#     # Date range for collection (using PTP Date range selected above)
#     if len(ptp_dates) > 0:
#         st.subheader("📅 Using Same Date Range as Above")
#         st.info(f"Analyzing collections from {ptp_start_date} to {ptp_end_date}")
        
#         # Filter: Collections > 0 BUT No PTP Status or No PTP Amount
#         collections_without_ptp = filtered_df[
#             (filtered_df['Collection Amount'] > 0) &
#             (
                
#                 (filtered_df['PTP Amount']==0)
#             )
#         ].copy()
        
#         # Further filter by date range if Collection Date is available
#         if 'Collection Date' in collections_without_ptp.columns:
#             collections_without_ptp = collections_without_ptp[
#                 (pd.to_datetime(collections_without_ptp['Collection Date'], errors='coerce').dt.date >= ptp_start_date) &
#                 (pd.to_datetime(collections_without_ptp['Collection Date'], errors='coerce').dt.date <= ptp_end_date)
#             ]
        
#         if len(collections_without_ptp) > 0:
#             # Calculate metrics
#             customers_no_ptp = collections_without_ptp['DisbursementID'].nunique()
#             total_collection_no_ptp = collections_without_ptp['Collection Amount'].sum()
#             total_comms_no_ptp = collections_without_ptp['Total Communications'].sum()
#             avg_collection_no_ptp = collections_without_ptp.groupby('DisbursementID')['Collection Amount'].sum().mean()
            
#             # Display metrics
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 st.metric("👥 Customers", f"{customers_no_ptp:,}")
#             with col2:
#                 st.metric("💵 Total Collection", f"₹{total_collection_no_ptp:,.0f}")
#             with col3:
#                 st.metric("📞 Communications", f"{total_comms_no_ptp:,}")
#             with col4:
#                 st.metric("📊 Avg per Customer", f"₹{avg_collection_no_ptp:,.0f}")
            
#             st.markdown("---")
            
#             # Branch-wise breakdown
#             st.subheader("🏢 Branch-wise Collections Without PTP")
            
#             branch_no_ptp = collections_without_ptp.groupby('Branch').agg({
#                 'DisbursementID': 'nunique',
#                 'Collection Amount': 'sum',
#                 'Total Communications': 'sum'
#             }).sort_values('Collection Amount', ascending=False).head(10)
            
#             branch_no_ptp.columns = ['Customers', 'Collection Amount (₹)', 'Communications']
            
#             fig_branch_no_ptp = px.bar(
#                 branch_no_ptp.reset_index(),
#                 x='Branch',
#                 y='Collection Amount (₹)',
#                 title='Top 10 Branches - Collections Without PTP',
#                 color='Collection Amount (₹)',
#                 color_continuous_scale='Blues',
#                 text='Collection Amount (₹)'
#             )
#             fig_branch_no_ptp.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
#             fig_branch_no_ptp = apply_chart_theme(fig_branch_no_ptp)
#             fig_branch_no_ptp.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
#             st.plotly_chart(fig_branch_no_ptp, width='stretch')
            
#             # Detailed table
#             st.subheader("📋 Customer Details - Collections Without PTP")
            
#             no_ptp_details = collections_without_ptp.groupby('DisbursementID').agg({
#                 'CustomerName': 'first',
#                 'Branch': 'first',
#                 'Collection Amount': 'sum',
#                 'Total Communications': 'sum',
#                 'PTP Status': 'first',
#                 'PTP Amount': 'first'
#             }).reset_index()
            
#             no_ptp_details.columns = ['Disbursement ID', 'Customer Name', 'Branch', 
#                                      'Collection Amount (₹)', 'Communications', 
#                                      'PTP Status', 'PTP Amount']
            
#             no_ptp_details['Collection Amount (₹)'] = no_ptp_details['Collection Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
#             no_ptp_details['PTP Status'] = no_ptp_details['PTP Status'].fillna('No PTP')
#             no_ptp_details['PTP Amount'] = no_ptp_details['PTP Amount'].fillna(0).apply(lambda x: f"₹{x:,.2f}" if x > 0 else 'No PTP')
            
#             st.dataframe(no_ptp_details, width='stretch', height=400)
            
#             # Download button
#             no_ptp_csv = no_ptp_details.to_csv(index=False).encode('utf-8')
#             st.download_button(
#                 label="📥 Download Collections Without PTP (CSV)",
#                 data=no_ptp_csv,
#                 file_name=f'collections_without_ptp_{ptp_start_date}_to_{ptp_end_date}.csv',
#                 mime='text/csv',
#             )
#         else:
#             st.info(f"No collections without PTP found in the date range {ptp_start_date} to {ptp_end_date}")
#     else:
#         st.info("No PTP Date data available for analysis.")
    
#     st.markdown("---")
    
#     # Section 6: Branch Performance
#     st.header("🏢 Branch Performance Analysis")
    
#     branch_performance = filtered_df.groupby('Branch').agg({
#         'Collection Amount': 'sum',
#         'Overdue Amount': 'sum',
#         'DisbursementID': 'nunique',
#         'Total Communications': 'sum'
#     }).round(2)
    
#     branch_performance['Collection Rate (%)'] = (
#         branch_performance['Collection Amount'] / branch_performance['Overdue Amount'] * 100
#     ).round(2)
#     branch_performance = branch_performance.sort_values('Collection Amount', ascending=False)
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.subheader("🏆 Top 5 Performing Branches")
#         top_5 = branch_performance.head(5)
#         fig_top = px.bar(
#             x=top_5.index,
#             y=top_5['Collection Amount'],
#             title='Top 5 Branches by Collection Amount',
#             labels={'x': 'Branch', 'y': 'Collection Amount (₹)'},
#             color=top_5['Collection Amount'],
#             color_continuous_scale='Greens',
#             text=top_5['Collection Amount']
#         )
#         fig_top.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
#         fig_top = apply_chart_theme(fig_top)
#         fig_top.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
#         st.plotly_chart(fig_top, width='stretch')
    
#     with col2:
#         st.subheader("⚠️ Bottom 5 Branches Needing Attention")
#         bottom_5 = branch_performance[branch_performance['Collection Amount'] > 0].tail(5)
#         fig_bottom = px.bar(
#             x=bottom_5.index,
#             y=bottom_5['Collection Amount'],
#             title='Bottom 5 Branches by Collection Amount',
#             labels={'x': 'Branch', 'y': 'Collection Amount (₹)'},
#             color=bottom_5['Collection Amount'],
#             color_continuous_scale='Reds',
#             text=bottom_5['Collection Amount']
#         )
#         fig_bottom.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
#         fig_bottom = apply_chart_theme(fig_bottom)
#         fig_bottom.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
#         st.plotly_chart(fig_bottom, width='stretch')
    
#     # Branch performance table
#     st.subheader("📋 Complete Branch Performance Table")
#     branch_display = branch_performance.copy()
#     branch_display['Collection Amount'] = branch_display['Collection Amount'].apply(lambda x: f"₹{x:,.2f}")
#     branch_display['Overdue Amount'] = branch_display['Overdue Amount'].apply(lambda x: f"₹{x:,.2f}")
#     branch_display.columns = ['Collection (₹)', 'Overdue (₹)', 'Unique Customers', 'Communications', 'Collection Rate (%)']
#     st.dataframe(branch_display, width='stretch', height=400)
    
#     st.markdown("---")
    
#     # Section 7: DPD Analysis
#     st.header("⏰ Days Past Due (DPD) Analysis")
    
#     # Create DPD buckets
#     def dpd_bucket(days):
#         if days == 0:
#             return '0 Days (Current)'
#         elif days <= 30:
#             return '1-30 Days'
#         elif days <= 60:
#             return '31-60 Days'
#         elif days <= 90:
#             return '61-90 Days'
#         elif days <= 180:
#             return '91-180 Days'
#         else:
#             return '180+ Days'
    
#     filtered_df['DPD_Bucket'] = filtered_df['NumberOfDaysPastDue'].apply(dpd_bucket)
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         dpd_count = filtered_df['DPD_Bucket'].value_counts()
#         bucket_order = ['0 Days (Current)', '1-30 Days', '31-60 Days', '61-90 Days', '91-180 Days', '180+ Days']
#         dpd_count = dpd_count.reindex(bucket_order, fill_value=0)
        
#         fig_dpd = px.bar(
#             x=dpd_count.index,
#             y=dpd_count.values,
#             title='Loan Distribution by DPD Bucket',
#             labels={'x': 'DPD Bucket', 'y': 'Number of Loans'},
#             color=dpd_count.values,
#             color_continuous_scale='RdYlGn_r',
#             text=dpd_count.values
#         )
#         fig_dpd.update_traces(texttemplate='%{text:,}', textposition='outside')
#         fig_dpd = apply_chart_theme(fig_dpd)
#         fig_dpd.update_layout(showlegend=False, height=400, xaxis_tickangle=-45)
#         st.plotly_chart(fig_dpd, width='stretch')
    
#     with col2:
#         dpd_amount = filtered_df.groupby('DPD_Bucket')['Overdue Amount'].sum()
#         dpd_amount = dpd_amount.reindex(bucket_order, fill_value=0)
        
#         fig_dpd_amount = px.pie(
#             values=dpd_amount.values,
#             names=dpd_amount.index,
#             title='Overdue Amount by DPD Bucket',
#             color_discrete_sequence=px.colors.sequential.RdBu_r,
#             hole=0.3
#         )
#         fig_dpd_amount.update_traces(textposition='inside', textinfo='percent+label')
#         fig_dpd_amount = apply_chart_theme(fig_dpd_amount)
#         fig_dpd_amount.update_layout(height=400)
#         st.plotly_chart(fig_dpd_amount, width='stretch')
    
#     st.markdown("---")
    
#     # Section 8: Active vs Inactive Loans
#     st.header("📊 Loan Portfolio Status")
    
#     col1, col2, col3 = st.columns([1, 1, 1])
    
#     active_count = len(filtered_df[filtered_df['IsActive'] == True])
#     inactive_count = len(filtered_df[filtered_df['IsActive'] == False])
    
#     with col1:
#         st.metric("✅ Active Loans", f"{active_count:,}")
    
#     with col2:
#         st.metric("❌ Inactive Loans", f"{inactive_count:,}")
    
#     with col3:
#         active_percentage = (active_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
#         st.metric("📈 Active Rate", f"{active_percentage:.1f}%")
    
#     # Visualization
#     loan_status_data = pd.DataFrame({
#         'Status': ['Active', 'Inactive'],
#         'Count': [active_count, inactive_count]
#     })
    
#     fig_status = px.pie(
#         loan_status_data,
#         values='Count',
#         names='Status',
#         title='Active vs Inactive Loans Distribution',
#         color='Status',
#         color_discrete_map={'Active': '#2ecc71', 'Inactive': '#e74c3c'},
#         hole=0.4
#     )
#     fig_status.update_traces(textposition='inside', textinfo='percent+label+value')
#     fig_status = apply_chart_theme(fig_status)
#     fig_status.update_layout(height=400)
#     st.plotly_chart(fig_status, width='stretch')
    
#     st.markdown("---")
    
#     # Section 9: Trend Analysis
#     st.header("📈 Trend Analysis Over Time")
    
#     daily_trends = filtered_df.groupby('Date').agg({
#         'Collection Amount': 'sum',
#         'Total Communications': 'sum',
#         'Overdue Amount': 'sum'
#     }).reset_index()
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         fig_collection_trend = px.line(
#             daily_trends,
#             x='Date',
#             y='Collection Amount',
#             title='Daily Collection Trend',
#             labels={'Collection Amount': 'Collection Amount (₹)'},
#             markers=True
#         )
#         fig_collection_trend.update_traces(line_color='#2ecc71', line_width=2)
#         fig_collection_trend = apply_chart_theme(fig_collection_trend)
#         fig_collection_trend.update_layout(height=400)
#         st.plotly_chart(fig_collection_trend, width='stretch')
    
#     with col2:
#         fig_comm_trend = px.line(
#             daily_trends,
#             x='Date',
#             y='Total Communications',
#             title='Daily Communication Volume',
#             labels={'Total Communications': 'Communications Sent'},
#             markers=True
#         )
#         fig_comm_trend.update_traces(line_color='#3498db', line_width=2)
#         fig_comm_trend = apply_chart_theme(fig_comm_trend)
#         fig_comm_trend.update_layout(height=400)
#         st.plotly_chart(fig_comm_trend, width='stretch')
    
#     st.markdown("---")
    
#     # Section 10: Summary Report
#     st.header("📄 Executive Summary Report")
    
#     summary_col1, summary_col2 = st.columns(2)
    
#     with summary_col1:
#         st.subheader("💼 Portfolio Overview")
#         st.write(f"**Total Unique Customers:** {total_unique_customers:,}")
#         st.write(f"**Active Loans:** {active_count:,}")
#         st.write(f"**Inactive Loans:** {inactive_count:,}")
#         st.write(f"**Total Branches:** {filtered_df['Branch'].nunique()}")
        
#         st.subheader("💰 Financial Metrics")
#         st.write(f"**Total Overdue Amount:** ₹{total_overdue_amount:,.2f}")
#         st.write(f"**Total Collection Amount:** ₹{total_collection_amount:,.2f}")
#         st.write(f"**Collection Rate:** {collection_rate:.2f}%")
#         st.write(f"**Total PTP Amount:** ₹{total_ptp_amount:,.2f}")
    
#     with summary_col2:
#         st.subheader("📞 Communication Summary")
#         st.write(f"**Total Communications:** {total_communications:,}")
#         st.write(f"**WhatsApp Messages:** {total_whatsapp_sent:,}")
#         st.write(f"**Blaster Calls:** {total_blaster_sent:,}")
#         st.write(f"**AI Calls:** {total_AI_Calls_sent:,}")
        
#         st.subheader("🎯 PTP Summary")
#         if len(ptp_data) > 0:
#             st.write(f"**Total PTPs:** {len(ptp_data):,}")
#             st.write(f"**Fulfilled:** {ptp_fulfilled:,}")
#             st.write(f"**Broken:** {ptp_broken:,}")
#             st.write(f"**Success Rate:** {ptp_success_rate:.1f}%")
#         else:
#             st.write("No PTP data available")
    
#     st.markdown("---")
    
#     # Section 11: Download Reports
#     st.header("📥 Download Reports")
    
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         csv = filtered_df.to_csv(index=False).encode('utf-8')
#         st.download_button(
#             label="📊 Download Filtered Data (CSV)",
#             data=csv,
#             file_name=f'filtered_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
#             mime='text/csv',
#         )
    
#     with col2:
#         branch_csv = branch_performance.to_csv().encode('utf-8')
#         st.download_button(
#             label="🏢 Download Branch Performance (CSV)",
#             data=branch_csv,
#             file_name=f'branch_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
#             mime='text/csv',
#         )
    
#     with col3:
#         if len(collection_data) > 0:
#             collection_csv = collection_data.to_csv(index=False).encode('utf-8')
#             st.download_button(
#                 label="💰 Download Collection Data (CSV)",
#                 data=collection_csv,
#                 file_name=f'collection_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
#                 mime='text/csv',
#             )
    
#     # Footer
#     st.markdown("---")
#     st.markdown(f"""
#         <div style='text-align: center; color: #000000; padding: 20px;'>
#             <p style='color: #000000;'><strong>Loan Collection Analytics Dashboard</strong></p>
#             <p style='color: #666666;'>Powered by Streamlit | Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
#         </div>
#     """, unsafe_allow_html=True)

# except FileNotFoundError:
#     st.error("⚠️ Error: 'Vinayna_Latest.csv' file not found. Please make sure the file is in the same directory as this script.")
#     st.info("📁 Place your 'Vinayna_Latest.csv' file in the same folder and refresh the page.")
# except Exception as e:
#     st.error(f"⚠️ An error occurred: {str(e)}")
#     st.info("Please check your data file and try again.")