from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    APP_NAME: str = 'Industrial IoT Cloud Platform'
    SECRET_KEY: str = 'change-this-secret'
    DATABASE_URL: str = 'mysql+pymysql://root:root123@127.0.0.1:3306/iiot_cloud'
    MQTT_ENABLED: bool = False
    MQTT_HOST: str = 'localhost'
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ''
    MQTT_PASSWORD: str = ''
    MQTT_TOPIC: str = '#'
    DATA_OFFLINE_SECONDS: int = 60
    class Config:
        env_file = '.env'
settings = Settings()
