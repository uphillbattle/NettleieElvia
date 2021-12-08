import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import datetime



class NettleieElvia(hass.Hass):

  def initialize(self):
    self.log_progress  = (self.args["log_progress"])
    self.set_request_data()
    self.run_in(self.hourly_call, 1)


  def hourly_call(self, kwargs):
    self.set_times()
    self.fetch_data(self.hourly_call, 60)
    self.set_states()

    self.next_call = self.next_hour_datetime.replace(second=5, microsecond=0, minute=0)
    self.run_at_handle = self.run_at(self.hourly_call, self.next_call)

    if (self.log_progress):
      self.output_log()

  
  def set_request_data(self):
    self.headers   = {"Ocp-Apim-Subscription-Key": self.args["ocp_apim_subscription_key"],
                      "Content-Type": "application/json"}
    self.url       = "https://elvia.azure-api.net/grid-tariff/api/1/tariffquery/meteringpointsgridtariffs"
    self.body      = {"meteringPointIds": [ self.args["malerid"] ]}


  def set_times(self):
    self.current_datetime   = datetime.datetime.now()
    self.next_hour_datetime = self.current_datetime + datetime.timedelta(hours=1)
    self.next_day_datetime  = self.current_datetime + datetime.timedelta(hours=48)
    self.pretty_last_hour   = str(self.current_datetime.year) + "-" + str(self.current_datetime.month).zfill(2) + "-" + \
                              str(self.current_datetime.day).zfill(2) + "T" + "00:00:00"
    self.pretty_next_hour   = str(self.next_day_datetime.year) + "-" + str(self.next_day_datetime.month).zfill(2) + "-" + \
                              str(self.next_day_datetime.day).zfill(2) + "T" + "00:00:00"

    self.body["startTime"]  = self.pretty_last_hour
    self.body["endTime"]    = self.pretty_next_hour

    self.current_hour       = self.current_datetime.hour

    self.todayString = str(self.current_datetime.year) + "-" + str(self.current_datetime.month).zfill(2) + "-" + \
                       str(self.current_datetime.day).zfill(2)


  def fetch_data(self, retry_function, wait_period):
    try:
      self.maler_response_json     = requests.post(self.url, json = self.body, headers = self.headers)
    except Exception as e:
      self.log('__function__: Ooops, API request failed, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      self.run_in(retry_function, wait_period)


  def set_states(self):
    self.maler_response = json.loads(self.maler_response_json.text)
    self.priceInfo      = self.maler_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"]

    self.variable_price_per_hour_array_today_raw    = []
    self.variable_price_per_hour_array_tomorrow_raw = []
    self.variable_price_per_hour_array_today        = []
    self.variable_price_per_hour_array_tomorrow     = []
    for element in self.priceInfo:
      startTime = element["startTime"]
      endTime   = element["expiredAt"]
      value     = element["variablePrice"]["total"]
      if startTime[0:10] == self.todayString:
        self.variable_price_per_hour_array_today_raw.append({"start": startTime, "end": endTime, "value": value})
        self.variable_price_per_hour_array_today.append(value)
      else:
        self.variable_price_per_hour_array_tomorrow_raw.append({"start": startTime, "end": endTime, "value": value})
        self.variable_price_per_hour_array_tomorrow.append(value)

    self.fixed_price_per_hour    = self.priceInfo[self.current_hour]["fixedPrices"][0]["priceLevel"][0]["total"]
    self.fixed_price_level       = self.priceInfo[self.current_hour]["fixedPrices"][0]["priceLevel"][0]["level"]
    self.variable_price_per_hour = self.priceInfo[self.current_hour]["variablePrice"]["total"]
    self.variable_price_level    = self.priceInfo[self.current_hour]["variablePrice"]["level"]

    self.set_state(self.args["sensorname"] + '_kapasitetsledd', \
                   state=self.fixed_price_per_hour, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' per time', \
                               'unit_of_measurement': 'NOK/h', \
                               'icon': 'mdi:currency-usd', \
                               'level': self.fixed_price_level})

    self.set_state(self.args["sensorname"] + '_forbruksledd', \
                   state=self.variable_price_per_hour, \
                   attributes={'friendly_name': self.args["sensoralias"] + ' per kWh', \
                               'unit_of_measurement': 'NOK/kWh', \
                               'icon': 'mdi:currency-usd', \
                               'level': self.variable_price_level,
                               'today': self.variable_price_per_hour_array_today, \
                               'tomorrow': self.variable_price_per_hour_array_tomorrow, \
                               'raw_today': self.variable_price_per_hour_array_today_raw, \
                               'raw_tomorrow': self.variable_price_per_hour_array_tomorrow_raw})


  def output_log(self):
    self.log("__function__: Time now              = %s" % self.current_datetime, log="main_log", level="INFO")
    self.log("__function__: Pretty Last hour      = %s" % self.pretty_last_hour, log="main_log", level="INFO")
    self.log("__function__: Pretty Next hour      = %s" % self.pretty_next_hour, log="main_log", level="INFO")
    self.log("__function__: kapasitetsledd (NOK/h)= %f" % self.fixed_price_per_hour, log="main_log", level="INFO")
    self.log("__function__: forbruksledd (NOK/kWh)= %f" % self.variable_price_per_hour, log="main_log", level="INFO")
    self.log("__function__: Next call             = %s" % self.next_call, log="main_log", level="INFO")
