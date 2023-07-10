## ERPNext Germany

App to hold regional code for Germany, built on top of ERPNext.

### Features

- Section for Register Information (Registerart, -gericht und nummer) in **Company**, **Customer** and **Supplier**

    ![Section with Register Information](docs/register_information.png)

- Validation of EU VAT IDs

   ![Validate EU VAT ID](docs/validate_vat_id.gif)

### HR

- Custom fields in **Employee** (tax information, etc.)
- List of religios denominations ("Konfessionen")
- List of German health insurance providers

    > Requires [HRMS](https://github.com/frappe/hrms) to be installed first.

- Holiday lists for all german states (via https://feiertage-api.de/)

    > Requires [HRMS](https://github.com/frappe/hrms) to be installed first.

## Installation

### On Frappe Cloud

1. Go to https://frappecloud.com/dashboard/#/sites and click the "New Site" button.
2. In Step 2 ("Select apps to install"), select "ERPNext", "HRMS" and "ERPNext Germany".
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
