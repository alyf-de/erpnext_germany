## ERPNext Germany

App to hold regional code for Germany, built on top of ERPNext.

> Currently this app is mostly empty. It holds the remains of the regional module in ERPNext that has been removed beginning with Version 14.

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
