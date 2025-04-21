## ERPNext Germany

App to hold regional code for Germany, built on top of ERPNext.

### Features

- German accounting reports

    - _Summen- und Saldenliste_

- Section for Register Information (Registerart, -gericht und nummer) in **Company**, **Customer** and **Supplier**

    ![Section with Register Information](docs/register_information.png)

- Validation of EU VAT IDs

    Automatically checks the validity of EU VAT IDs of all your customers every three months, or manually whenever you want. Check out the [intro on Youtube](https://youtu.be/hsFMn2Y85zA) (german).

    ![Validate EU VAT ID](docs/vat_check.png)

- Allow deletion of the most recent sales transaction only

    This ensures consecutive numbering of transactions. Applies to **Quotation**, **Sales Order**, **Sales Invoice**.

- Restrict deletion of attachments to submitted transactions
- Custom fields in **Employee** (tax information, etc.)
- List of religios denominations ("Konfessionen")
- List of German health insurance providers (depends on HRMS)
- Create **Business Letters** from a template and print or email them to your customers or suppliers
- Record **Business Trips** and pay out allowances to your employees (dt. Reisekostenabrechnung) (depends on HRMS)

## Installation

> [!NOTE]
> Some features of this app depend on the [HRMS](https://github.com/frappe/hrms) app. If you want to use them, you need to install the HRMS app before installing this app.

### On Frappe Cloud

You can find ERPNext Germany in the [Frappe Cloud Marketplace](https://frappecloud.com/marketplace/apps/erpnext_germany).
Please refer to the [Frappe Cloud documentation](https://frappecloud.com/docs/installing-an-app) on how to install an app.

### Local

Using bench, [install ERPNext](https://github.com/frappe/bench#installation) as mentioned here.

Once ERPNext is installed, add the ERPNext Germany app to your bench by running

```bash
bench get-app https://github.com/alyf-de/erpnext_germany.git
```

After that, you can install the app on required site (let's say demo.com ) by running

```bash
bench --site demo.com install-app erpnext_germany
```

## Business Trip

Before an employee can create a **Business Trip (Dienstreise)**, you should configure the available regions and their travel allowances in the **Business Trip Region** list. A basic list based on the German tax law is imported on installation, but not further updated later. In the **Business Trip Settings (Dienstreise-Einstellungen)** you can set the value for the mileage allowance and select **Expense Claim Type** for mileage allowance and **Additional meal expenses**. Both Expense Claim Type are preset to **Additional meal expenses**. If you have HRMS installed, it allows you to book expenses as Expense Claims.

When a **Business Trip** is submitted, it creates a draft **Expense Claim** for the employee's travel allowances including the Additional meal expenses as well as mileage allowance for "Car (private)". One business trip will create on **Expense Claim** which can be approved and submitted as usual.

Mileage allowance is calculated based on the distance entered in the details of the journey when "Car (private)" is selected.

The Additional meal expenses depend on the selected region. Select the "From" and "To" dates of the trip and with the click on "Add Row" all days of the trip a pre-created.

The receipts for transport and accommodation can be attached, but are not processed automatically. You can check them, create a **Purchase Invoice** and pay the respective amount to the employee.

You can use our [Banking app](https://github.com/alyf-de/banking) to reconcile the **Expense Claims** and **Purchase Invoices** with the respective **Bank Transactions**.

### License

GNU GPL V3. See the `LICENSE` file for more information.
