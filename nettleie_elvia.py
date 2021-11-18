import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import datetime



class NettleieElvia(hass.Hass):

  def initialize(self):
    self.log_progress  = (self.args["log_progress"])
    self.set_request_data()
    self.hourly_call()


  def hourly_call(self):
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
    self.bodyoppe  = {"meteringPointIds": [ self.args["malerid_oppe"] ]}
    self.bodynede  = {"meteringPointIds": [ self.args["malerid_nede"] ]}
    self.bodyhytta = {"meteringPointIds": [ self.args["malerid_hytta"] ]}


  def set_times(self):
    self.current_datetime   = datetime.datetime.now()
    self.next_hour_datetime = self.current_datetime + datetime.timedelta(hours=1)
    self.pretty_last_hour   = str(self.current_datetime.year) + "-" + str(self.current_datetime.month).zfill(2) + "-" + \
                              str(self.current_datetime.day).zfill(2) + "T" + str(self.current_datetime.hour).zfill(2) + ":00:00"
    self.pretty_next_hour   = str(self.next_hour_datetime.year) + "-" + str(self.next_hour_datetime.month).zfill(2) + "-" + \
                              str(self.next_hour_datetime.day).zfill(2) + "T" + str(self.next_hour_datetime.hour).zfill(2) + ":00:00"

    self.bodyoppe["startTime"]  = self.pretty_last_hour
    self.bodyoppe["endTime"]    = self.pretty_next_hour
    self.bodynede["startTime"]  = self.pretty_last_hour
    self.bodynede["endTime"]    = self.pretty_next_hour
    self.bodyhytta["startTime"] = self.pretty_last_hour
    self.bodyhytta["endTime"]   = self.pretty_next_hour


  def fetch_data(self, retry_function, wait_period):
    try:
      self.maler_oppe_response_json     = requests.post(self.url, json = self.bodyoppe, headers = self.headers)
      self.maler_nede_response_json     = requests.post(self.url, json = self.bodynede, headers = self.headers)
      self.maler_hytta_response_json    = requests.post(self.url, json = self.bodyhytta, headers = self.headers)
    except Exception as e:
      self.log('__function__: Ooops, API request failed, retrying in {} seconds...\n{}'.format(wait_period, e), log="main_log", level="WARNING")
      run_in(retry_function, wait_period)


  def set_states(self):
    self.maler_oppe_response          = json.loads(self.maler_oppe_response_json.text)
    self.fixed_price_per_hour_oppe    = self.maler_oppe_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    self.variable_price_per_hour_oppe = self.maler_oppe_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hjemme_oppe_kapasitetsledd', state=self.fixed_price_per_hour_oppe,    attributes={'friendly_name': 'Nettleie per time hjemme oppe', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hjemme_oppe_forbruksledd',  state=self.variable_price_per_hour_oppe, attributes={'friendly_name': 'Nettleie per kWh hjemme oppe', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    self.maler_nede_response          = json.loads(self.maler_nede_response_json.text)
    self.fixed_price_per_hour_nede    = self.maler_nede_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    self.variable_price_per_hour_nede = self.maler_nede_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hjemme_nede_kapasitetsledd', state=self.fixed_price_per_hour_nede,    attributes={'friendly_name': 'Nettleie per time hjemme nede', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hjemme_nede_forbruksledd',  state=self.variable_price_per_hour_nede, attributes={'friendly_name': 'Nettleie per kWh hjemme nede', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    self.maler_hytta_response          = json.loads(self.maler_hytta_response_json.text)
    self.fixed_price_per_hour_hytta    = self.maler_hytta_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    self.variable_price_per_hour_hytta = self.maler_hytta_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hytta_kapasitetsledd', state=self.fixed_price_per_hour_hytta,    attributes={'friendly_name': 'Nettleie per time hytta', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hytta_forbruksledd',  state=self.variable_price_per_hour_hytta, attributes={'friendly_name': 'Nettleie per kWh hytta', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})


  def output_log(self):
    self.log("__function__: Time now                    = %s" % self.current_datetime, log="main_log", level="INFO")
    self.log("__function__: Pretty Last hour            = %s" % self.pretty_last_hour, log="main_log", level="INFO")
    self.log("__function__: Pretty Next hour            = %s" % self.pretty_next_hour, log="main_log", level="INFO")
    self.log("__function__: oppe  kapasitetsledd (NOK/h)= %f" % self.fixed_price_per_hour_oppe, log="main_log", level="INFO")
    self.log("__function__: oppe  forbruksledd (NOK/kWh)= %f" % self.variable_price_per_hour_oppe, log="main_log", level="INFO")
    self.log("__function__: nede  kapasitetsledd (NOK/h)= %f" % self.fixed_price_per_hour_nede, log="main_log", level="INFO")
    self.log("__function__: nede  forbruksledd (NOK/kWh)= %f" % self.variable_price_per_hour_nede, log="main_log", level="INFO")
    self.log("__function__: hytta kapasitetsledd (NOK/h)= %f" % self.fixed_price_per_hour_hytta, log="main_log", level="INFO")
    self.log("__function__: hytta forbruksledd (NOK/kWh)= %f" % self.variable_price_per_hour_hytta, log="main_log", level="INFO")
    self.log("__function__: Next call                   = %s" % self.next_call, log="main_log", level="INFO")
