# Używamy obrazu Python 3.10 jako podstawowego
FROM python:3.10-slim

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# Kopiujemy pliki aplikacji do kontenera
COPY . /app

# Zmienna ARG dla API key (przekazana przez GitHub Actions)
ARG SHOPIFY_API_KEY

# Ustawiamy zmienną środowiskową w kontenerze
ENV SHOPIFY_API_KEY=${SHOPIFY_API_KEY}

# Instalujemy zależności z pliku requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Otwieramy port (jeśli aplikacja będzie miała serwer HTTP lub inną komunikację)
EXPOSE 8000

# Ustawiamy komendę do uruchomienia aplikacji
CMD ["python", "main.py"]
