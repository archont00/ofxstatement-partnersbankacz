This is a parser for CSV transaction history exported from Partners Banka, a.s. (Czech Republic)
from within the mobile app (Account // ... (more) // Documents // Generate statement)

The expected field separator is semicolumn (";") and character encoding UTF-8

It is a plugin for `ofxstatement`_.

.. _ofxstatement: https://github.com/kedder/ofxstatement

Usage
=====
::

  $ ofxstatement convert -t partnersbankacz:SA vypis_3408294210_20240505_20240531.csv vypis_3408294210_20240505_20240531.ofx

Configuration
=============
::

  $ ofxstatement edit-config

and set e.g. the following:
::

  [partnersbankacz:SA]
  plugin = partnersbankacz
  currency = CZK
  account = Partners Banka SA
  account_type = SAVINGS

  [partnersbankacz:CA]
  plugin = partnersbankacz
  currency = CZK
  account = Partners Banka CA
  account_type = CHECKING

Issues
======

Partners Banka is fresh newcomer to the market and things may change - especially the payment types list is not complete yet.

Feel free to create GitHub pull request to accomodate for the changes.