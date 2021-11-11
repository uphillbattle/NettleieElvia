import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import datetime



class NettleieElvia(hass.Hass):

  def initialize(self):
    self._initialize()


  def _initialize(self):
    self.log_progress  = (self.args["log_progress"])

    current_datetime   = datetime.datetime.now()
    next_hour_datetime = current_datetime + datetime.timedelta(hours=1)
    pretty_last_hour   = str(current_datetime.year) + "-" + str(current_datetime.month).zfill(2) + "-" + \
                         str(current_datetime.day).zfill(2) + "T" + str(current_datetime.hour).zfill(2) + ":00:00"
    pretty_next_hour   = str(next_hour_datetime.year) + "-" + str(next_hour_datetime.month).zfill(2) + "-" + \
                         str(next_hour_datetime.day).zfill(2) + "T" + str(next_hour_datetime.hour).zfill(2) + ":00:00"

    self.headers   = {"Ocp-Apim-Subscription-Key": self.args["ocp_apim_subscription_key"],
                      "Content-Type": "application/json"}
    self.bodyoppe  = {"startTime": pretty_last_hour,
                      "endTime": pretty_next_hour,
                      "meteringPointIds": [ self.args["malerid_oppe"] ]}
    self.bodynede  = {"startTime": pretty_last_hour,
                      "endTime": pretty_next_hour,
                      "meteringPointIds": [ self.args["malerid_nede"] ]}
    self.bodyhytta = {"startTime": pretty_last_hour,
                      "endTime": pretty_next_hour,
                      "meteringPointIds": [ self.args["malerid_hytta"] ]}
    self.url       = "https://elvia.azure-api.net/grid-tariff/api/1/tariffquery/meteringpointsgridtariffs"

    try:
      maler_oppe_response_json     = requests.post(self.url, json = self.bodyoppe, headers = self.headers)
      maler_nede_response_json     = requests.post(self.url, json = self.bodynede, headers = self.headers)
      maler_hytta_response_json    = requests.post(self.url, json = self.bodyhytta, headers = self.headers)
    except Exception as e:
      self.log('__function__: Ooops, API request failed, retrying in 60 seconds...\n{}'.format(e), log="main_log", level="WARNING")
      run_in(self._initialize, 60)

    maler_oppe_response          = json.loads(maler_oppe_response_json.text)
    fixed_price_per_hour_oppe    = maler_oppe_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    variable_price_per_hour_oppe = maler_oppe_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hjemme_oppe_per_time', state=fixed_price_per_hour_oppe,    attributes={'friendly_name': 'Nettleie per time hjemme oppe', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hjemme_oppe_per_kwh',  state=variable_price_per_hour_oppe, attributes={'friendly_name': 'Nettleie per kWh hjemme oppe', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    maler_nede_response          = json.loads(maler_nede_response_json.text)
    fixed_price_per_hour_nede    = maler_nede_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    variable_price_per_hour_nede = maler_nede_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hjemme_nede_per_time', state=fixed_price_per_hour_nede,    attributes={'friendly_name': 'Nettleie per time hjemme nede', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hjemme_nede_per_kwh',  state=variable_price_per_hour_nede, attributes={'friendly_name': 'Nettleie per kWh hjemme nede', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    maler_hytta_response          = json.loads(maler_hytta_response_json.text)
    fixed_price_per_hour_hytta    = maler_hytta_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    variable_price_per_hour_hytta = maler_hytta_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hytta_per_time', state=fixed_price_per_hour_hytta,    attributes={'friendly_name': 'Nettleie per time hytta', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hytta_per_kwh',  state=variable_price_per_hour_hytta, attributes={'friendly_name': 'Nettleie per kWh hytta', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    next_call = next_hour_datetime.replace(second=5, microsecond=0, minute=0)
    self.run_at_handle = self.run_at(self.hourly_call, next_call)

    if (self.log_progress):
      self.log("__function__: Time now                    = %s" % current_datetime, log="main_log", level="INFO")
      self.log("__function__: Pretty Last hour            = %s" % pretty_last_hour, log="main_log", level="INFO")
      self.log("__function__: Pretty Next hour            = %s" % pretty_next_hour, log="main_log", level="INFO")
      self.log("__function__: oppe  fixedPrice per hour   = %f" % fixed_price_per_hour_oppe, log="main_log", level="INFO")
      self.log("__function__: oppe  variablePrice per kWh = %f" % variable_price_per_hour_oppe, log="main_log", level="INFO")
      self.log("__function__: nede  fixedPrice per hour   = %f" % fixed_price_per_hour_nede, log="main_log", level="INFO")
      self.log("__function__: nede  variablePrice per kWh = %f" % variable_price_per_hour_nede, log="main_log", level="INFO")
      self.log("__function__: hytta fixedPrice per hour   = %f" % fixed_price_per_hour_hytta, log="main_log", level="INFO")
      self.log("__function__: hytta variablePrice per kWh = %f" % variable_price_per_hour_hytta, log="main_log", level="INFO")
      self.log("__function__: Next call                   = %s" % next_call, log="main_log", level="INFO")


  def hourly_call(self, kwargs):
    current_datetime   = datetime.datetime.now()
    next_hour_datetime = current_datetime + datetime.timedelta(hours=1)
    pretty_last_hour   = str(current_datetime.year) + "-" + str(current_datetime.month).zfill(2) + "-" + \
                         str(current_datetime.day).zfill(2) + "T" + str(current_datetime.hour).zfill(2) + ":00:00"
    pretty_next_hour   = str(next_hour_datetime.year) + "-" + str(next_hour_datetime.month).zfill(2) + "-" + \
                         str(next_hour_datetime.day).zfill(2) + "T" + str(next_hour_datetime.hour).zfill(2) + ":00:00"
    self.bodyoppe  = {"startTime": pretty_last_hour,
                      "endTime": pretty_next_hour,
                      "meteringPointIds": [ self.args["malerid_oppe"] ]}
    self.bodynede  = {"startTime": pretty_last_hour,
                      "endTime": pretty_next_hour,
                      "meteringPointIds": [ self.args["malerid_nede"] ]}
    self.bodyhytta = {"startTime": pretty_last_hour,
                      "endTime": pretty_next_hour,
                      "meteringPointIds": [ self.args["malerid_hytta"] ]}

    try:
      maler_oppe_response_json     = requests.post(self.url, json = self.bodyoppe, headers = self.headers)
      maler_nede_response_json     = requests.post(self.url, json = self.bodynede, headers = self.headers)
      maler_hytta_response_json    = requests.post(self.url, json = self.bodyhytta, headers = self.headers)
    except Exception as e:
      self.log('__function__: Ooops, API request failed, retrying in 60 seconds...\n{}'.format(e), log="main_log", level="WARNING")
      run_in(self.hourly_call, 60)

    maler_oppe_response          = json.loads(maler_oppe_response_json.text)
    fixed_price_per_hour_oppe    = maler_oppe_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    variable_price_per_hour_oppe = maler_oppe_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hjemme_oppe_per_time', state=fixed_price_per_hour_oppe,    attributes={'friendly_name': 'Nettleie per time hjemme oppe', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hjemme_oppe_per_kwh',  state=variable_price_per_hour_oppe, attributes={'friendly_name': 'Nettleie per kWh hjemme 54 oppe', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    maler_nede_response          = json.loads(maler_nede_response_json.text)
    fixed_price_per_hour_nede    = maler_nede_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    variable_price_per_hour_nede = maler_nede_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hjemme_nede_per_time', state=fixed_price_per_hour_nede,    attributes={'friendly_name': 'Nettleie per time hjemme nede', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hjemme_nede_per_kwh',  state=variable_price_per_hour_nede, attributes={'friendly_name': 'Nettleie per kWh hjemme nede', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    maler_hytta_response          = json.loads(maler_hytta_response_json.text)
    fixed_price_per_hour_hytta    = maler_hytta_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["fixedPrices"][0]["priceLevel"][0]["total"]
    variable_price_per_hour_hytta = maler_hytta_response["gridTariffCollections"][0]["gridTariff"]["tariffPrice"]["priceInfo"][0]["variablePrice"]["total"]
    self.set_state('sensor.nettleie_hytta_per_time', state=fixed_price_per_hour_hytta,    attributes={'friendly_name': 'Nettleie per time hytta', 'unit_of_measurement': 'NOK/h', 'icon': 'mdi:currency-usd'})
    self.set_state('sensor.nettleie_hytta_per_kwh',  state=variable_price_per_hour_hytta, attributes={'friendly_name': 'Nettleie per kWh hytta', 'unit_of_measurement': 'NOK/kWh', 'icon': 'mdi:currency-usd'})

    next_call = next_hour_datetime.replace(second=5, microsecond=0, minute=0)
    self.run_at_handle = self.run_at(self.hourly_call, next_call)

    if (self.log_progress):
      self.log("__function__: Time now                    = %s" % current_datetime, log="main_log", level="INFO")
      self.log("__function__: Pretty Last hour            = %s" % pretty_last_hour, log="main_log", level="INFO")
      self.log("__function__: Pretty Next hour            = %s" % pretty_next_hour, log="main_log", level="INFO")
      self.log("__function__: oppe  fixedPrice per hour   = %f" % fixed_price_per_hour_oppe, log="main_log", level="INFO")
      self.log("__function__: oppe  variablePrice per kWh = %f" % variable_price_per_hour_oppe, log="main_log", level="INFO")
      self.log("__function__: nede  fixedPrice per hour   = %f" % fixed_price_per_hour_nede, log="main_log", level="INFO")
      self.log("__function__: nede  variablePrice per kWh = %f" % variable_price_per_hour_nede, log="main_log", level="INFO")
      self.log("__function__: hytta fixedPrice per hour   = %f" % fixed_price_per_hour_hytta, log="main_log", level="INFO")
      self.log("__function__: hytta variablePrice per kWh = %f" % variable_price_per_hour_hytta, log="main_log", level="INFO")
      self.log("__function__: Next call                   = %s" % next_call, log="main_log", level="INFO")