# NettleieElvia

*Updated on 2022-07-06:* 
Update to new formats in connection with new tariffs from 1st July 2022.

A very crude AppDaemon app for use with Home Assistant that fetches grid tariffs (NOK per hour and NOK per kWh) from Elvia's new GridTariff API (https://elvia.portal.azure-api.net/). Refer to the API for documentation (https://assets.ctfassets.net/jbub5thfds15/3Jm2yspPw1kFmDEkzdjhfw/e3a153543d8f95e889285248e5af21af/Elvia_GridTariffAPI_for_smart_house_purposes_DIGIN.pdf) and guidance for getting a subscription key (https://www.elvia.no/smart-forbruk/api-for-nettleie-priser-kan-gjore-hjemmet-ditt-smartere/). 

The app fetches grid tariffs for one meter and can be instantiated for several meters in `apps.yaml`.

As of April 2022 the app is not particularly useful since the grid tariffs (for consumers) is constant (except summer/winter tariffs in some areas). However, the gridd tariff is expected to change during 2022, so that the variable grid tariffs (NOK/kWh) will change on an hourly basis and the fixed grid tariffs (NOK/h) will change on a monthly basis.

The app fetches the grid tariffs 5 seconds into each hour. Since the tariffs will not change more often than hourly, fetching it more often is pointless. Elvia has set an API call limit of 200 calls per hour per user, so if you have 3 meters, you could call the API every minute (180 calls per hour) instead of every hour (3 calls per hour), but why would you?

I'm quite sure that someone will make a better integration for Home Assistant fairly soon - at which time this app will be obsolete - and I'm looking forward to that.

In `apps.yaml`, one argument is `log_progress`. When set to `true`, the app will output a log on every (hourly) run to the Appdaemon log. Set it to `false` to turn that off.

If fetching grid tariffs fails for some reason, the app will output a warning to the Appdaemon log and try again once every second minute until successful. If you have more than 6 meters (or more than 3 meters and two Home Assistant instances, you can do the math), and to avoid hitting the API call limitation, increase the waiting period in this line (the number is the number of seconds to the next attempt - so here every two minutes):

```
      self.fetch_data(self.hourly_call, 120)
```
