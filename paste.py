# 🔥 BILL TABLE FORMAT
            st.markdown("## Parking Bill")

            bill_df = pd.DataFrame({
                "Field": ["Vehicle Number", "Entry Time", "Exit Time", "Duration", "Rate"],
                "Details": [
                    plate,
                    entry_time.strftime("%H:%M:%S"),
                    exit_time.strftime("%H:%M:%S"),
                    f"{duration_minutes} minutes",
                    f"₹{rate} / min"
                ]
            })

            st.table(bill_df)

            st.markdown("---")

            # 🔥 BIG TOTAL
            st.markdown(f"# 💰 ₹ {amount}")

            st.markdown("---")

            # 🔥 CENTERED QR + TEXT
            col1, col2, col3 = st.columns([1,2,1])

            with col2:
                st.markdown("### Scan this QR for e-bill")
                if os.path.exists("payment_qr.png"):
                    st.image("payment_qr.png", width=250)
                else:
                    st.warning("payment_qr.png not found")

        st.session_state.detected_plate = ""
