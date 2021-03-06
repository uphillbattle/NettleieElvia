import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import datetime
import time



class NettleieElvia(hass.Hass):

  def initialize(self):
    self.log_progress  = (self.args["log_progress"])
    self.set_request_data()
    self.set_correction_data()
    self.run_in(self.hourly_call, 1)


  def hourly_call(self, kwargs):
    self.set_times()
    self.fetch_data(self.hourly_call, 120)
    self.set_correction()
    self.set_states(self.hourly_call, 120)

    self.next_call = self.next_hour_datetime.replace(second=5, microsecond=0, minute=0)
    self.run_at_handle = self.run_at(self.hourly_call, self.next_call)

    if (self.log_progress):
      self.output_log()

  
  def set_request_data(self):
    self.headers   = {"X-API-Key": self.args["x_api_key"],
                      "Content-Type": "application/json",
                      "Cache-Control": "no-cache"}
    self.url       = "https://elvia.azure-api.net/grid-tariff/digin/api/1.0/tariffquery/meteringpointsgridtariffs"
    self.body      = {"meteringPointIds": [ self.args["meterid"] ]}

  def set_correction_data(self):
    self.end_correction_period = datetime.datetime(2022, 4, 1)
    self.correction_amount     = (0.1669 - 0.0891)*1.25

  def set_times(self):
    localtime = time.localtime()
    if localtime.tm_isdst > 0:
        zoneadjust = "+02:00"
    else:
        zoneadjust = "+01:00"
    self.current_datetime   = datetime.datetime.now()
    self.next_hour_datetime = self.current_datetime + datetime.timedelta(hours=1)
    self.tomorrow_datetime  = self.current_datetime + datetime.timedelta(hours=24)
    self.next_day_datetime  = self.current_datetime + datetime.timedelta(hours=48)
    self.pretty_last_night  = str(self.current_datetime.year) + "-" + str(self.current_datetime.month).zfill(2) + "-" + \
                              str(self.current_datetime.day).zfill(2) + "T" + "00:00:00" + zoneadjust
    self.pretty_next_night  = str(self.next_day_datetime.year) + "-" + str(self.next_day_datetime.month).zfill(2) + "-" + \
                              str(self.next_day_datetime.day).zfill(2) + "T" + "00:00:00" + zoneadjust
    self.pretty_now         = str(self.current_datetime.year) + "-" + str(self.current_datetime.month).zfill(2) + "-" + \
                              str(self.current_datetime.day).zfill(2) + "T" + str(self.current_datetime.hour).zfill(2) + ":" + \
                              str(self.current_datetime.minute).zfill(2) + ":" + str(self.current_datetime.second).zfill(2) + \
                              zoneadjust

    self.body["startTime"]  = self.pretty_last_night
    self.body["endTime"]    = self.pretty_next_night

    self.current_hour       = self.current_datetime.hour

    self.todayString = str(self.current_datetime.year) + "-" + str(self.current_datetime.month).zfill(2) + "-" + \
                       str(self.current_datetime.day).zfill(2)


  def fetch_data(self, retry_function, wait_period):
    try:
      self.maler_response_json     = requests.post(self.url, json = self.body, headers = self.headers)
    except Exception as e:
      self.log('__function__: Ooops, API request failed, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)


  def set_correction(self):
    if (self.current_datetime < self.end_correction_period):
      self.correction_today = self.correction_amount
    else:
      self.correction_today = 0.0
    if (self.tomorrow_datetime < self.end_correction_period):
      self.correction_tomorrow = self.correction_amount
    else:
      self.correction_tomorrow = 0.0


  def set_states(self, retry_function, wait_period):
    try:
      self.maler_response = json.loads(self.maler_response_json.text)
    except Exception as e:
      self.log('__function__: Ooops, API response could not be read, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)
    self.priceInfo      = self.maler_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]

    self.variable_price_per_hour_array_today_raw    = []
    self.variable_price_per_hour_array_tomorrow_raw = []
    self.variable_price_per_hour_array_today        = []
    self.variable_price_per_hour_array_tomorrow     = []
    for element in self.priceInfo["hours"]:
      startTime = element["startTime"]
      endTime   = element["expiredAt"]
      value     = element["energyPrice"]["total"]
      if startTime[0:10] == self.todayString:
        self.variable_price_per_hour_array_today_raw.append({"start": startTime, "end": endTime, "value": value - self.correction_today})
        self.variable_price_per_hour_array_today.append(value - self.correction_today)
        if ((self.pretty_now >= startTime) and (self.pretty_now < endTime)):
            self.variable_price_per_hour = value - self.correction_today
            forLoopBreak = False
            fixedPriceLevelId = self.maler_response["gridTariffCollections"][0]["meteringPointsAndPriceLevels"][0]["currentFixedPriceLevel"]["levelId"]
            for fixedPriceElement in self.priceInfo["priceInfo"]["fixedPrices"]:
                if (element["fixedPrice"]["id"] == fixedPriceElement["id"]):
                    for priceLevelsElement in fixedPriceElement["priceLevels"]:
                        if (priceLevelsElement["id"] == fixedPriceLevelId):
                            hourPrices = priceLevelsElement["hourPrices"][0]
                            self.fixed_price_per_hour = hourPrices["total"]
                            forLoopBreak = True
                            break
                    if (forLoopBreak == True):
                        break
      else:
        self.variable_price_per_hour_array_tomorrow_raw.append({"start": startTime, "end": endTime, "value": value - self.correction_tomorrow})
        self.variable_price_per_hour_array_tomorrow.append(value - self.correction_tomorrow)

    self.set_state(self.args["sensorname"] + '_kapasitetsledd', \
                   state=self.fixed_price_per_hour, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' per time', \
                               'unit_of_measurement': 'NOK/h', \
                               'icon': 'mdi:currency-usd'})

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
    self.log("__function__: Pretty time now       = %s" % self.pretty_now, log="main_log", level="INFO")
    self.log("__function__: Pretty Last night     = %s" % self.pretty_last_night, log="main_log", level="INFO")
    self.log("__function__: Pretty Next night     = %s" % self.pretty_next_night, log="main_log", level="INFO")
    self.log("__function__: kapasitetsledd (NOK/h)= %f" % self.fixed_price_per_hour, log="main_log", level="INFO")
    self.log("__function__: forbruksledd (NOK/kWh)= %f" % self.variable_price_per_hour, log="main_log", level="INFO")
    self.log("__function__: Next call             = %s" % self.next_call, log="main_log", level="INFO")
