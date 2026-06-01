import machine
import dht
import ssd1306
import time
import neopixel
import ujson
import network
import usmtp
import urequests

from umqtt.simple import MQTTClient

#---------------------PINAGEM---------------------------

pins  = {
    "dht22": 19,
    "mq2": 35,
    "ldr": 32,
    "pir": 16,

    "sda": 12,
    "scl": 14,
    "buzzer": 18,
    "servo": 5,
    "relay": 17,
    "ring": 4
}

#----------------------SENSORES-------------------------

#Temperatura e Umidade
senDht22 = dht.DHT22(machine.Pin(pins["dht22"]))

#Gas
senMq2 = machine.ADC(machine.Pin(pins["mq2"]))
senMq2.atten(machine.ADC.ATTN_11DB)

#Luminosidade
senLdr = machine.ADC(machine.Pin(pins["ldr"]))
senLdr.atten(machine.ADC.ATTN_11DB)

#Movimento
senPir = machine.Pin(pins["pir"])

#----------------------ATUADORES------------------------

#OLED
sda = machine.Pin(pins["sda"])
scl = machine.Pin(pins["scl"])
i2c = machine.I2C(0, scl=scl, sda=sda)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

#Buzina
buzzer = machine.PWM(machine.Pin(pins["buzzer"]))
buzzer.duty(0)
buzzer.freq(523)

def alarm():

    for i in range (3):

        #Intensidade
        buzzer.duty(512)
        #Espera
        time.sleep(0.5)
        #Desligar
        buzzer.duty(0)
        time.sleep(0.1)
       
#Motor
servo = machine.PWM(machine.Pin(pins["servo"]))
servo.freq(50)

def spin(angle):

    #Conversão
    duty = int((angle / 180) * 102 + 26)

    servo.duty(duty)

#Relay
relay = machine.Pin(pins["relay"], machine.Pin.OUT)

def relayOn():

    relay.on()

    time.sleep(1)

    relay.off()

#Ring
lightNum = 24

ring = neopixel.NeoPixel(machine.Pin(pins["ring"]), lightNum)

def ringOn(r,g,b,mode):

    if(mode == "load"):

        for i in range(lightNum):
            ring[i] = (r, g, b)

            ring.write()

            time.sleep(0.3)

    elif(mode == "flash"):

        for i in range(lightNum):
            ring[i] = (r, g, b)

        ring.write()

        time.sleep(0.3)

        for i in range(lightNum):
            ring[i] = (0, 0, 0)

        ring.write()

# #----------------------WI-FI-------------------------------

# Credenciais do Wifi
ssid = "Wokwi-GUEST"
password = ""

# Criando Conexão Wifi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)

print("Conectando ao WiFi...")
while not wifi.isconnected():
    time.sleep(1)

print("WiFi conectado!")


# #-------------------------MQTT------------------------

#Criando Client MQTT
client = MQTTClient(
    "",
    "",
    port="",
    user="",
    password="",
    ssl=True,
    ssl_params={'server_hostname': ""}
)

#Criando Função de CallBack
def callback(topic, msg):

    action = msg.decode()

    print(action)

    if action == "relay_on":

        relay.on()

    elif action == "relay_off":

        relay.off()

    elif action == "alarm":

        alarm()

    elif action == "servo_open":

        spin(179)

    elif action == "servo_close":

        spin(0)
    
    elif action == "ring_on":
        ringOn(0,255,0,"load")

client.set_callback(callback)

# Criando Conexão MQTT
client.connect()

#inscrevendo no tópico de ações
client.subscribe(b"resauto/action")

def publishMQTT(dados):

    client.publish(
        "resauto/data",
        ujson.dumps(dados)
    )


#------------------------SHEETS-----------------------

appScriptsURL = ""


def sendSheets(dados):

    try:

        headers = {
            "Content-Type": "application/json"
        }

        response = urequests.post(
            appScriptsURL,
            data=ujson.dumps(dados),
            headers=headers
        )

        print("Sheets:", response.text)

        response.close()

    except Exception as e:
        print("Erro Google Sheets:", e)

#------------------------E-MAIL-----------------------

emailSender = ""
emailKey = ""
emailRecipient = ""

def sendEmail(dados, alerta):

    subject = "Alerta de Automações"

    message = f"""\
Subject: {subject}

Sistema de Automacao Residencial
Luiz Eduardo Dias - 11231104074

{alerta}:

Dados atuais dos sensores:

Temperatura: {dados["Temperatura"]} C

Umidade: {dados["Umidade"]} %

Gas: {dados["Gas"]}

Luminosidade: {dados["Luminosidade"]}

Movimento: {dados["Movimento"]}

Mensagem enviada automaticamente pelo ESP32.
    """

    try:

        smtp = usmtp.SMTPSession(
            host="smtp.gmail.com",
            port=465,
            ssl_context=True
        )

        smtp.login(
            emailSender,
            emailKey
        )

        smtp.sendmail(
            emailSender,
            emailRecipient,
            message
        )

        smtp.quit()

        print("Email enviado!")

    except Exception as e:
        print("Erro email:", e)

#-------------------TESTE DE ATUADORES-----------------

alarm()

spin(0)

relayOn()

ringOn(128, 0, 128, "load")

# sendSheets()

# sendEmail()

#-------------------MEDIÇÃO DE BACKUP-----------------

#Medidas DHT22
senDht22.measure()
temp = senDht22.temperature()
hum = senDht22.humidity()

#Medidas MQ2
gas = senMq2.read()

#Medidas LDR
lum = senLdr.read()

#Medidas PIR
mov = senPir.value()

#Backup para envio MQTT
backup = {
    "Temperatura": temp,
    "Umidade": hum,
    "Gas": gas,
    "Luminosidade": lum,
    "Movimento": mov
}

publishMQTT(backup)

#Backup para email e Sheets
alerts = {
    "Temperatura": 0,
    "Umidade": 0,
    "Gas": 0,
    "Luminosidade": 0,
    "Movimento": 0
}

lastAlertData = {
    "Temperatura": None,
    "Umidade": None,
    "Gas": None,
    "Luminosidade": None,
    "Movimento": None
}

cooldownAlert = 60000

#-----------------------EXECUÇÃO----------------------

while True:

    #Checando mensagens no tópico
    client.check_msg()

    #Medidas DHT22
    senDht22.measure()
    temp = senDht22.temperature()
    hum = senDht22.humidity()

    #Medidas MQ2
    gas = senMq2.read()
    
    #Medidas LDR
    lum = senLdr.read()
    
    #Medidas PIR
    mov = senPir.value()

    #Exibir OLED
    oled.fill(0)
    oled.text(f"Temperatura: {temp}", 0, 0)
    oled.text(f"Umidade: {hum}", 0, 10)
    oled.text(f"Gas: {gas}", 0, 20)
    oled.text(f"Luminosidade: {lum}", 0, 30)
    oled.text(f"Movimento: {mov}", 0, 40)
    oled.show()

    #Estruturação para envios
    data = {
        "Temperatura": temp,
        "Umidade": hum,
        "Gas": gas,
        "Luminosidade": lum,
        "Movimento": mov
    }

    #Verificação de mudança para envio
    if data != backup:
        print("Enviando MQTT...")
        publishMQTT(data)
        backup = data

    #----------------------ALERTAS--------------------------

    #Pegando o tempo de agora desde a execução
    now = time.ticks_ms()

    if not (18 < temp < 35):

        oled.text("ALERTA DE TEMPERATURA", 0, 50)

        oled.show()

        alarm()

        ringOn(255, 0, 0, "flash")

        #Calculando a diferença desde o inicio da execução
        diff = time.ticks_diff(
            now,
            alerts["Temperatura"]
        )

        lastValue = lastAlertData["Temperatura"]

        #Se já tiver passando 2min e o valor for diferente do ultimo alerta
        if diff >= cooldownAlert and temp != lastValue:

            #Salvando o ultimo tempo
            alerts["Temperatura"] = now

            #Salvando o ultimo Valor
            lastAlertData["Temperatura"] = temp

            print("ALERTANDO")

            sendSheets(data)

            sendEmail(data, "ALERTA DE TEMPERATURA")


    if not (30 < hum < 75):

        oled.text("ALERTA DE UMIDADE", 0, 50)

        oled.show()

        alarm()

        ringOn(255, 0, 0, "flash")

        #Calculando a diferença desde o inicio da execução
        diff = time.ticks_diff(
            now,
            alerts["Umidade"]
        )

        lastValue = lastAlertData["Umidade"]

        #Se já tiver passando 2min e o valor for diferente do ultimo alerta
        if diff >= cooldownAlert and hum != lastValue:

            #Salvando o ultimo tempo
            alerts["Umidade"] = now

            #Salvando o ultimo Valor
            lastAlertData["Umidade"] = hum

            print("ALERTANDO")

            sendSheets(data)

            sendEmail(data, "ALERTA DE UMIDADE")


    if not (1000 < gas < 4000):

        oled.text("ALERTA DE GAS", 0, 50)

        oled.show()

        alarm()

        ringOn(255, 0, 0, "flash")

        #Calculando a diferença desde o inicio da execução
        diff = time.ticks_diff(
            now,
            alerts["Gas"]
        )

        lastValue = lastAlertData["Gas"]

        #Se já tiver passando 2min e o valor for diferente do ultimo alerta
        if diff >= cooldownAlert and gas != lastValue:

            #Salvando o ultimo tempo
            alerts["Gas"] = now

            #Salvando o ultimo Valor
            lastAlertData["Gas"] = gas

            print("ALERTANDO")

            sendSheets(data)

            sendEmail(data, "ALERTA DE GAS")


    if not (200 < lum < 3500):

        oled.text("ALERTA DE LUMINOSIDADE", 0, 50)

        oled.show()

        alarm()

        ringOn(255, 0, 0, "flash")

        #Calculando a diferença desde o inicio da execução
        diff = time.ticks_diff(
            now,
            alerts["Luminosidade"]
        )

        lastValue = lastAlertData["Luminosidade"]

        #Se já tiver passando 2min e o valor for diferente do ultimo alerta
        if diff >= cooldownAlert and lum != lastValue:

            #Salvando o ultimo tempo
            alerts["Luminosidade"] = now

            #Salvando o ultimo Valor
            lastAlertData["Luminosidade"] = lum

            print("ALERTANDO")

            sendSheets(data)

            sendEmail(data, "ALERTA DE LUMINOSIDADE")


    if mov == 1:

        oled.text("ALERTA DE MOVIMENTO", 0, 50)

        oled.show()

        alarm()

        ringOn(255, 0, 0, "flash")

        #Calculando a diferença desde o inicio da execução
        diff = time.ticks_diff(
            now,
            alerts["Movimento"]
        )

        lastValue = lastAlertData["Movimento"]

        #Se já tiver passando 2min e o valor for diferente do ultimo alerta
        if diff >= cooldownAlert and mov != lastValue:

            #Salvando o ultimo tempo
            alerts["Movimento"] = now

            #Salvando o ultimo Valor
            lastAlertData["Movimento"] = mov

            print("ALERTANDO")

            sendSheets(data)

            sendEmail(data, "ALERTA DE MOVIMENTO")

    time.sleep(0.1)