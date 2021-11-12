# NettleieElvia

A very crude AppDaemon app for use with Home Assistant that fetches grid tariffs (NOK per hour and NOK per kWh) from Elvia's new GridTariff API (https://elvia.portal.azure-api.net/). Refer to the API for documentation (https://assets.ctfassets.net/jbub5thfds15/1mF3J3xVf9400SDuwkChUC/a069a61a0257ba8c950432000bdefef3/Elvia_GridTariffAPI_for_smart_house_purposes_v1_1_20210212.doc.pdf) and guidance for getting a subscription key (https://www.elvia.no/smart-forbruk/api-for-nettleie-priser-kan-gjore-hjemmet-ditt-smartere/). 

The app here fetches grid tariffs for three meters for one owner. If you have more or less than three meters, then add or remove relevant code sections in `apps.yaml` and `nettleie_elvia.py`.

In 2021 the app is not particularly useful since the grid tariffs (for consumers) is constant (except summer/winter tariffs in some areas). Starting 1 January 2022, however, the variable grid tariffs (NOK/kWh) will change on an hourly basis and the fixed grid tariffs (NOK/h) will change on a monthly basis.

The app fetches the grid tariffs 5 seconds into each hour. Since the tariffs will not change more often than hourly, fetching it more often is pointless. Elvia has set an API call limit of 200 calls per hour per user, so if you have 3 meters, you could call the API every minute (180 calls per hour) instead of every hour (3 calls per hour), but why would you?

I'm quite sure that someone will make a better integration for Home Assistant fairly soon - at which time this app will be obsolete - and I'm looking forward to that.

In `apps.yaml`, one argument is `log_progress`. When set to `true`, the app will output a log on every (hourly) run to the Appdaemon log. Set it to `false` to turn that off.

If fetching grid tariffs fail for some reason, the app will output a warning to the Appdaemon log and try again once a minute until successful. If you have more than 3 meters, and to avoid hitting the API call limitation, increase the waiting period in these lines (the number is the number of seconds to the next attempt - so here every minute):

```
      self.fetch_data(self._initialize, 60)
```

```
      self.fetch_data(self.hourly_call, 60)
```
