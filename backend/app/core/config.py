class Settings:
    def __init__ (self):
        self.app_name = "Resume Parser API"
        self.version = "1.0.0"
        self.debug = True
        self.allowed_hosts = ["*"]
        
settings = Settings()