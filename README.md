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

    > [!INFO]
    > Currently, we always check four customers that didn't have a VAT ID Check in the last three months. If these four all have an invalid VAT ID, we get stuck.

- Allow deletion of the most recent sales transaction only

    This ensures consecutive numbering of transactions. Applies to **Quotation**, **Sales Order**, **Sales Invoice**.

- Custom fields in **Employee** (tax information, etc.)
- List of religios denominations ("Konfessionen")
- List of German health insurance providers

    Requires [HRMS](https://github.com/frappe/hrms) to be installed first.

- Create **Business Letters** from a template and print or email them to your customers or suppliers

## Installation

### On Frappe Cloud

1. Go to https://frappecloud.com/dashboard/#/sites and click the "New Site" button.
2. In Step 2 ("Select apps to install"), select "ERPNext" and "ERPNext Germany".
3. Complete the new site wizard.

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

### License

GNU GPL V3. See the `LICENSE` file for more information.
