# NettleieElvia

An AppDaemon app that fetches grid tariffs (NOK per hour and NOK per kWh) from Elvia's new GridTariff API (https://elvia.portal.azure-api.net/). Refer to the API for documentation (https://assets.ctfassets.net/jbub5thfds15/1mF3J3xVf9400SDuwkChUC/a069a61a0257ba8c950432000bdefef3/Elvia_GridTariffAPI_for_smart_house_purposes_v1_1_20210212.doc.pdf) and guidance for getting a subscription key. 

The app here fetches grid tariffs for three meters for one owner. If you have more or less than three meters, then add or remove relevant code sections in apps.yaml and nettleie_elvia.py.
