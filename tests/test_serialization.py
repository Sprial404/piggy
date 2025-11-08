import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from piggy.installment_plan import InstallmentPlan, Installment, PaymentStatus


class TestInstallmentPlanSerialization(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.sample_plan = InstallmentPlan(
            merchant_name="Tech Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 15),
            installments=[
                Installment(
                    installment_number=1,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 2, 15),
                    status=PaymentStatus.PAID,
                    paid_date=date(2024, 2, 10)
                ),
                Installment(
                    installment_number=2,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 3, 15),
                    status=PaymentStatus.PENDING
                ),
                Installment(
                    installment_number=3,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 4, 15),
                    status=PaymentStatus.PENDING
                )
            ]
        )

    def test_json_serialization_to_string(self):
        """Test JSON serialization to string"""
        json_str = self.sample_plan.to_json()
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed['merchant_name'], "Tech Store")
        self.assertEqual(parsed['total_amount'], "1200.00")
        self.assertEqual(len(parsed['installments']), 3)

    def test_json_serialization_to_file(self):
        """Test JSON serialization to file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Serialize to file
            result = self.sample_plan.to_json(tmp_path)
            
            # Verify file was created and contains valid JSON
            self.assertTrue(Path(tmp_path).exists())
            file_content = Path(tmp_path).read_text()
            self.assertEqual(result, file_content)
            
            # Verify content is valid JSON
            parsed = json.loads(file_content)
            self.assertEqual(parsed['merchant_name'], "Tech Store")
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_json_deserialization_from_string(self):
        """Test JSON deserialization from string"""
        json_str = self.sample_plan.to_json()
        restored_plan = InstallmentPlan.from_json(json_str)
        
        # Verify all data is preserved
        self.assertEqual(restored_plan.merchant_name, self.sample_plan.merchant_name)
        self.assertEqual(restored_plan.total_amount, self.sample_plan.total_amount)
        self.assertEqual(restored_plan.purchase_date, self.sample_plan.purchase_date)
        self.assertEqual(len(restored_plan.installments), len(self.sample_plan.installments))
        
        # Check first installment details
        original_inst = self.sample_plan.installments[0]
        restored_inst = restored_plan.installments[0]
        self.assertEqual(restored_inst.installment_number, original_inst.installment_number)
        self.assertEqual(restored_inst.amount, original_inst.amount)
        self.assertEqual(restored_inst.due_date, original_inst.due_date)
        self.assertEqual(restored_inst.status, original_inst.status)
        self.assertEqual(restored_inst.paid_date, original_inst.paid_date)

    def test_json_deserialization_from_file(self):
        """Test JSON deserialization from file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Save to file
            self.sample_plan.to_json(tmp_path)
            
            # Load from file
            restored_plan = InstallmentPlan.from_json_file(tmp_path)
            
            # Verify data integrity
            self.assertEqual(restored_plan.merchant_name, self.sample_plan.merchant_name)
            self.assertEqual(restored_plan.total_amount, self.sample_plan.total_amount)
            self.assertEqual(restored_plan.remaining_balance, self.sample_plan.remaining_balance)
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_csv_export(self):
        """Test CSV export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Export to CSV
            self.sample_plan.to_csv(tmp_path)
            
            # Verify file was created
            self.assertTrue(Path(tmp_path).exists())
            
            # Read and verify content
            content = Path(tmp_path).read_text()
            lines = content.strip().split('\n')

            # Check header matches flattened CSV format
            expected_headers = 'merchant_name,total_amount,purchase_date,created_at,updated_at,installment_number,amount,due_date,status,paid_date,is_paid,is_pending,is_overdue'
            self.assertEqual(lines[0], expected_headers)

            # Verify key data appears in CSV
            self.assertIn('Tech Store', content)
            self.assertIn('1200.00', content)

            # Should have header + 3 installment rows
            self.assertEqual(len(lines), 4)
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_roundtrip_json_integrity(self):
        """Test that data survives JSON roundtrip without loss"""
        # Serialize and deserialize
        json_str = self.sample_plan.to_json()
        restored_plan = InstallmentPlan.from_json(json_str)
        
        # Check calculated properties are preserved
        self.assertEqual(restored_plan.remaining_balance, self.sample_plan.remaining_balance)
        self.assertEqual(restored_plan.is_fully_paid, self.sample_plan.is_fully_paid)
        self.assertEqual(restored_plan.next_payment_due, self.sample_plan.next_payment_due)
        self.assertEqual(restored_plan.num_installments, self.sample_plan.num_installments)


if __name__ == '__main__':
    unittest.main()