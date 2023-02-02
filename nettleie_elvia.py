import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import datetime
import time



class NettleieElvia(hass.Hass):

  def initialize(self):
    self.log_progress  = (self.args["log_progress"])
    self.set_request_data()
    self.run_in(self.hourly_call, 1)


  def hourly_call(self, kwargs):
    self.set_times()
    self.fetch_data(self.hourly_call, 120)
    self.set_states(self.hourly_call, 120)

    self.next_call = self.next_hour_datetime.replace(second=5, microsecond=0, minute=0)
    self.run_at_handle = self.run_at(self.hourly_call, self.next_call)

    if (self.log_progress):
      self.output_log()

  
  def set_request_data(self):
    self.headers_tariff   = {"X-API-Key": self.args["x_api_key"],
                             "Content-Type": "application/json",
                             "Cache-Control": "no-cache"}
    self.url_tariff       = "https://elvia.azure-api.net/grid-tariff/digin/api/1.0/tariffquery/meteringpointsgridtariffs"
    self.body_tariff      = {"meteringPointIds": [ self.args["meterid"] ]}
    self.headers_maxhours = {"Authorization": "Bearer " + self.args["token"]}
    self.url_maxhours     = "https://elvia.azure-api.net/customer/metervalues/api/v2/maxhours?meteringPointIds=" + self.args["meterid"]


  def set_times(self):
    dtnow   = datetime.datetime.now()
    tnow    = time.localtime()
    dstnow  = tnow.tm_isdst
    if dstnow > 0:
      zoneadjust = "+02:00"
    else:
      zoneadjust = "+01:00"
    dtlast  = datetime.datetime(dtnow.year, dtnow.month, dtnow.day, 0, 0, 0)
    tlast   = time.localtime(dtlast.timestamp())
    dstlast = tlast.tm_isdst
    if dstlast > 0:
      dtlast = dtlast - datetime.timedelta(hours=2)
    else:
      dtlast = dtlast - datetime.timedelta(hours=1)
    dt48    = dtnow + datetime.timedelta(days=2)
    dtnext  = datetime.datetime(dt48.year, dt48.month, dt48.day, 0, 0, 0)
    tnext   = time.localtime(dtnext.timestamp())
    dstnext = tnext.tm_isdst
    if dstnext > 0:
      dtnext = dtnext - datetime.timedelta(hours=2)
    else:
      dtnext = dtnext - datetime.timedelta(hours=1)

    self.current_datetime   = datetime.datetime.now()
    self.next_hour_datetime = self.current_datetime + datetime.timedelta(hours=1)
    self.pretty_last_night  = str(dtlast.year) + "-" + str(dtlast.month).zfill(2) + "-" + \
                              str(dtlast.day).zfill(2) + "T" + str(dtlast.hour).zfill(2) + ":00:00+00:00"
    self.pretty_next_night  = str(dtnext.year) + "-" + str(dtnext.month).zfill(2) + "-" + \
                              str(dtnext.day).zfill(2) + "T" + str(dtnext.hour).zfill(2) + ":00:00+00:00"
    self.pretty_now         = str(dtnow.year) + "-" + str(dtnow.month).zfill(2) + "-" + \
                              str(dtnow.day).zfill(2) + "T" + str(dtnow.hour).zfill(2) + ":" + \
                              str(dtnow.minute).zfill(2) + ":" + str(dtnow.second).zfill(2) + \
                              zoneadjust
    self.body_tariff["startTime"]  = self.pretty_last_night
    self.body_tariff["endTime"]    = self.pretty_next_night
    self.todayString = str(dtnow.year) + "-" + str(dtnow.month).zfill(2) + "-" + \
                       str(dtnow.day).zfill(2)


  def fetch_data(self, retry_function, wait_period):
    try:
      self.tariff_response_json    = requests.post(self.url_tariff, json = self.body_tariff, headers = self.headers_tariff)
    except Exception as e:
      self.log('__function__: Ooops, tariff API request failed, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)
    try:
      self.maxhours_response_json  = requests.get(self.url_maxhours, headers = self.headers_maxhours)
    except Exception as e:
      self.log('__function__: Ooops, maxhours API request failed, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)


  def set_states(self, retry_function, wait_period):
    try:
      self.tariff_response = json.loads(self.tariff_response_json.text)
    except Exception as e:
      self.log('__function__: Ooops, tariff API response could not be read, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)
    self.priceInfo      = self.tariff_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]

    self.variable_price_per_hour_array_today_raw    = []
    self.variable_price_per_hour_array_tomorrow_raw = []
    self.variable_price_per_hour_array_today        = []
    self.variable_price_per_hour_array_tomorrow     = []
    for element in self.priceInfo["hours"]:
      startTime = element["startTime"]
      endTime   = element["expiredAt"]
      value     = element["energyPrice"]["total"]
      if startTime[0:10] == self.todayString:
        self.variable_price_per_hour_array_today_raw.append({"start": startTime, "end": endTime, "value": value})
        self.variable_price_per_hour_array_today.append(value)
        if ((self.pretty_now >= startTime) and (self.pretty_now < endTime)):
            self.variable_price_per_hour = value
            forLoopBreak = False
            fixedPriceLevelId = self.tariff_response["gridTariffCollections"][0]["meteringPointsAndPriceLevels"][0]["currentFixedPriceLevel"]["levelId"]
            for fixedPriceElement in self.priceInfo["priceInfo"]["fixedPrices"]:
                if (element["fixedPrice"]["id"] == fixedPriceElement["id"]):
                    for priceLevelsElement in fixedPriceElement["priceLevels"]:
                        if (priceLevelsElement["id"] == fixedPriceLevelId):
                            hourPrices = priceLevelsElement["hourPrices"][0]
                            self.fixed_price_per_hour = hourPrices["total"]
                            self.fixed_price_levelInfo = priceLevelsElement["levelInfo"]
                            self.fixed_price_per_month = priceLevelsElement["monthlyTotal"]
                            forLoopBreak = True
                            break
                    if (forLoopBreak == True):
                        break
      else:
        self.variable_price_per_hour_array_tomorrow_raw.append({"start": startTime, "end": endTime, "value": value})
        self.variable_price_per_hour_array_tomorrow.append(value)

    try:
      self.maxhours_response = json.loads(self.maxhours_response_json.text)
    except Exception as e:
      self.log('__function__: Ooops, maxhours API response could not be read, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)

    self.maxhours_max_consumption_this_month     = []
    self.maxhours_max_consumption_last_month     = []
    self.maxhours_average_consumption_this_month = [] 
    self.maxhours_average_consumption_last_month = []
    for element in self.maxhours_response["meteringpoints"][0]["maxHoursAggregate"]:
      if element["noOfMonthsBack"] == 0:
        self.maxhours_average_consumption_this_month = element["averageValue"]
        for maxHoursElement in element["maxHours"]:
          self.maxhours_max_consumption_this_month.append({"startTime": maxHoursElement["startTime"], "value": maxHoursElement["value"]})
      else:
        self.maxhours_average_consumption_last_month = element["averageValue"]
        for maxHoursElement in element["maxHours"]:
          self.maxhours_max_consumption_last_month.append({"startTime": maxHoursElement["startTime"], "value": maxHoursElement["value"]})

    self.set_state(self.args["sensorname"] + '_kapasitetsledd', \
                   state=self.fixed_price_per_hour, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' per time', \
                               'unit_of_measurement': 'NOK/h', \
                               'icon': 'mdi:currency-usd', \
                               'level_info': self.fixed_price_levelInfo, \
                               'monthly_total': self.fixed_price_per_month, \
                               'average_max_consumption_this_month': self.maxhours_average_consumption_this_month, \
                               'max_hourly_consumptions_this_month': self.maxhours_max_consumption_this_month, \
                               'average_max_consumption_last_month': self.maxhours_average_consumption_last_month, \
                               'max_hourly_consumptions_last_month': self.maxhours_max_consumption_last_month})
    self.set_state(self.args["sensorname"] + '_kapasitetsledd_trinn',\
                   state=self.fixed_price_levelInfo, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' kapasitetsledd trinn', \
                               'icon': 'mdi:stairs', \
                               'level_info': self.fixed_price_levelInfo, \
                               'monthly_total': self.fixed_price_per_month, \
                               'average_max_consumption_this_month': self.maxhours_average_consumption_this_month, \
                               'max_hourly_consumptions_this_month': self.maxhours_max_consumption_this_month, \
                               'average_max_consumption_last_month': self.maxhours_average_consumption_last_month, \
                               'max_hourly_consumptions_last_month': self.maxhours_max_consumption_last_month})
    self.set_state(self.args["sensorname"] + '_kapasitetsledd_mnd',\
                   state=self.fixed_price_per_month, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' kapasitetsledd per måned', \
                               'unit_of_measurement': 'NOK/mnd', \
                               'icon': 'mdi:currency-usd', \
                               'level_info': self.fixed_price_levelInfo, \
                               'monthly_total': self.fixed_price_per_month, \
                               'average_max_consumption_this_month': self.maxhours_average_consumption_this_month, \
                               'max_hourly_consumptions_this_month': self.maxhours_max_consumption_this_month, \
                               'average_max_consumption_last_month': self.maxhours_average_consumption_last_month, \
                               'max_hourly_consumptions_last_month': self.maxhours_max_consumption_last_month})
    self.set_state(self.args["sensorname"] + '_effekt',\
                   state=self.maxhours_average_consumption_this_month, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' kapasitetsleddsbestemmende effekt', \
                               'unit_of_measurement': 'kWh/h', \
                               'icon': 'mdi:lightning-bolt', \
                               'level_info': self.fixed_price_levelInfo, \
                               'monthly_total': self.fixed_price_per_month, \
                               'average_max_consumption_this_month': self.maxhours_average_consumption_this_month, \
                               'max_hourly_consumptions_this_month': self.maxhours_max_consumption_this_month, \
                               'average_max_consumption_last_month': self.maxhours_average_consumption_last_month, \
                               'max_hourly_consumptions_last_month': self.maxhours_max_consumption_last_month})

    self.set_state(self.args["sensorname"] + '_forbruksledd', \
                   state=self.variable_price_per_hour, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' per kWh', \
                               'unit_of_measurement': 'NOK/kWh', \
                               'icon': 'mdi:currency-usd',
                               'today': self.variable_price_per_hour_array_today, \
                               'tomorrow': self.variable_price_per_hour_array_tomorrow, \
                               'raw_today': self.variable_price_per_hour_array_today_raw, \
                               'raw_tomorrow': self.variable_price_per_hour_array_tomorrow_raw})


  def output_log(self):
    self.log("__function__: Time now              = %s" % self.current_datetime, log="main_log", level="INFO")
    self.log("__function__: Pretty Last night     = %s" % self.pretty_last_night, log="main_log", level="INFO")
    self.log("__function__: Pretty Next night     = %s" % self.pretty_next_night, log="main_log", level="INFO")
    self.log("__function__: kapasitetsledd (NOK/h)= %f" % self.fixed_price_per_hour, log="main_log", level="INFO")
    self.log("__function__: forbruksledd (NOK/kWh)= %f" % self.variable_price_per_hour, log="main_log", level="INFO")
    self.log("__function__: Next call             = %s" % self.next_call, log="main_log", level="INFO")
