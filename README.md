## ERPNext Germany

App to hold regional code for Germany, built on top of ERPNext.

### Introduction

ERPNext Germany aims to support regional customizations for Germany. The app is built on Frappe, a full-stack, meta-data driven, web framework, and integrates seamlessly with ERPNext, the most agile ERP software.

Customizations include:

1. Datev Settings -
The german DATEV eG is a registered cooperative of the tax, accountancy and legal professions. DATEV Settings is a DocType where users can configure DATEV settings that are applied for a company and it has all the necessary fields.


2. DATEV Report -
ERPNext Germany has a report called DATEV. It helps to generate the DATEV format which is a CSV-based file interface for importing data into DATEV Accounting.
### Installation

Using bench, [install ERPNext](https://github.com/frappe/bench#installation) as mentioned here.

Once ERPNext is installed, add ERPNext Germany app to your bench by running

```sh
$ bench get-app https://github.com/frappe/erpnext_germany.git
```

After that, you can install the app on required site (let's say demo.com )by running

```sh
$ bench --site demo.com install-app erpnext_germany
```

### License

GNU GPL V3. See [license.txt](https://github.com/frappe/erpnext_germany/blob/develop/license.txt) for more information.
