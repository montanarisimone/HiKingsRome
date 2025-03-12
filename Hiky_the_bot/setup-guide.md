# Guida Completa per HikyTheBot

## 1. Configurazione Iniziale della VM

1. **Clonare il repository GitHub**:
   ```bash
   git clone https://github.com/montanarisimone/HiKingsRome.git
   cd HiKingsRome/Hiky_the_bot
   ```

2. **Creare e attivare l'ambiente virtuale**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Installare le dipendenze**:
   ```bash
   pip install python-telegram-bot==13.7 pytz requests python-dotenv
   ```

4. **Configurare il file .env con le variabili d'ambiente**:
   ```bash
   nano .env
   ```
   Contenuto da aggiungere:
   ```
   TELEGRAM_TOKEN=il_tuo_token_bot_telegram
   TELEGRAM_GROUP_ID=il_tuo_id_gruppo_telegram
   OPENWEATHER_API_KEY=la_tua_api_key_openweather
   ```

5. **Inizializzare il database**:
   ```bash
   chmod +x setup_database.py
   python setup_database.py
   ```
   Durante la configurazione, aggiungere un utente amministratore (con Telegram ID).

## 2. Configurazione del Servizio Systemd

1. **Creare il file di servizio**:
   ```bash
   sudo nano /etc/systemd/system/hikybot.service
   ```
   Contenuto:
   ```
   [Unit]
   Description=HikyTheBot Telegram Bot
   After=network.target

   [Service]
   User=hikingsrome
   WorkingDirectory=/home/hikingsrome/HiKingsRome/Hiky_the_bot
   ExecStart=/home/hikingsrome/HiKingsRome/Hiky_the_bot/venv/bin/python /home/hikingsrome/HiKingsRome/Hiky_the_bot/HikyTheBot.py
   Restart=always
   RestartSec=10
   StandardOutput=syslog
   StandardError=syslog
   SyslogIdentifier=hikybot

   [Install]
   WantedBy=multi-user.target
   ```

2. **Abilitare e avviare il servizio**:
   ```bash
   sudo systemctl enable hikybot.service
   sudo systemctl start hikybot.service
   ```

3. **Verificare lo stato del servizio**:
   ```bash
   sudo systemctl status hikybot.service
   ```

## 3. Configurazione del Backup Automatico

1. **Creare lo script di backup**:
   ```bash
   mkdir -p ~/HiKingsRome/Hiky_the_bot/utils
   nano ~/HiKingsRome/Hiky_the_bot/utils/backup_database.py
   ```
   Copiare lo script di backup Python fornito.

2. **Rendere lo script eseguibile**:
   ```bash
   chmod +x ~/HiKingsRome/Hiky_the_bot/utils/backup_database.py
   ```

3. **Configurare cron per i backup automatici**:
   ```bash
   crontab -e
   ```
   Aggiungere la riga:
   ```
   0 1 * * * cd ~/HiKingsRome/Hiky_the_bot && python ~/HiKingsRome/Hiky_the_bot/utils/backup_database.py --db-path ~/HiKingsRome/Hiky_the_bot/hiky_bot.db --backup-dir ~/backups --days 7
   ```

## 4. Operazioni di Manutenzione

### Aggiornare il Bot da GitHub

Quando viene aggiornato il codice su GitHub:

1. **Fermare il servizio**:
   ```bash
   sudo systemctl stop hikybot.service
   ```

2. **Scaricare le modifiche**:
   ```bash
   cd ~/HiKingsRome
   git pull
   ```

3. **Riavviare il servizio**:
   ```bash
   sudo systemctl start hikybot.service
   ```

4. **Verificare lo stato**:
   ```bash
   sudo systemctl status hikybot.service
   ```

### Modificare le Variabili d'Ambiente

Se devi modificare le variabili d'ambiente:

1. **Modificare il file .env**:
   ```bash
   cd ~/HiKingsRome/Hiky_the_bot
   nano .env
   ```

2. **Riavviare il servizio per applicare le modifiche**:
   ```bash
   sudo systemctl restart hikybot.service
   ```

### Verificare i Log del Bot

Per controllare i log in caso di problemi:
```bash
sudo journalctl -u hikybot.service -n 100
```

Per seguire i log in tempo reale:
```bash
sudo journalctl -u hikybot.service -f
```

### Eseguire il Backup Manuale

Per eseguire un backup manuale:
```bash
cd ~/HiKingsRome/Hiky_the_bot
python utils/backup_database.py --db-path hiky_bot.db --backup-dir ~/backups --days 7
```

## 5. Comandi del Bot

I comandi configurati nel bot sono:
- `/menu` - Apre il menu principale
- `/restart` - Riavvia la conversazione
- `/privacy` - Gestisci le impostazioni della privacy
- `/bug` - Segnala un bug
- `/admin` - Pannello di amministrazione (solo admin)

## 6. Risoluzione dei Problemi

Se il bot non funziona correttamente:

1. **Controllare lo stato del servizio**:
   ```bash
   sudo systemctl status hikybot.service
   ```

2. **Verificare i log per errori**:
   ```bash
   sudo journalctl -u hikybot.service -n 100
   ```

3. **Controllare manualmente il bot**:
   ```bash
   cd ~/HiKingsRome/Hiky_the_bot
   source venv/bin/activate
   python HikyTheBot.py
   ```

4. **Verificare il database**:
   ```bash
   sqlite3 ~/HiKingsRome/Hiky_the_bot/hiky_bot.db
   .tables
   SELECT * FROM users LIMIT 5;
   .quit
   ```

## 7. Suggerimenti per l'Ottimizzazione

1. **Monitorare l'uso delle risorse** periodicamente:
   ```bash
   htop
   ```

2. **Controllare lo spazio su disco** per assicurarsi che i backup non lo saturino:
   ```bash
   df -h
   ```

3. **Verificare regolarmente i backup** per assicurarsi che funzionino correttamente:
   ```bash
   ls -la ~/backups
   ```

4. **Considerare un sistema di monitoraggio** per ricevere avvisi in caso di problemi con il bot.
