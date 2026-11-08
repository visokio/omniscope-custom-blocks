# Writes the invented OpenWeatherMap responses in tests/canned/ that the tests serve instead of live calls.
# The shapes follow OpenWeatherMap's documented answers for /data/2.5/weather and /data/2.5/forecast;
# every value is invented. Run from the repository root:
#   Rscript Connectors/Weather/OpenWeatherMap/tests/make_canned.R
library(jsonlite)
dir <- "Connectors/Weather/OpenWeatherMap/tests/canned"
sites <- read.csv("Connectors/Weather/OpenWeatherMap/sample-data/sites.csv", stringsAsFactors = FALSE)
sites <- sites[!is.na(sites$Latitude), ]
set.seed(7)
conditions <- list(
  list(id = 500, main = "Rain", description = "light rain", icon = "10d"),
  list(id = 803, main = "Clouds", description = "broken clouds", icon = "04d"),
  list(id = 800, main = "Clear", description = "clear sky", icon = "01d"),
  list(id = 701, main = "Mist", description = "mist", icon = "50d"),
  list(id = 600, main = "Snow", description = "light snow", icon = "13d")
)
now <- as.numeric(as.POSIXct("2026-11-06 12:00:00", tz = "UTC"))
w <- function(x) write(x, file.path(dir, paste0(attr(x, "file"))))
for (i in seq_len(nrow(sites))) {
  s <- sites[i, ]
  cond <- conditions[[c(1, 2, 3, 4, 5, 2)[i]]]
  temp <- round(runif(1, 3, 12), 2)
  if (cond$main == "Snow") temp <- round(temp - 6, 2)  # snow falls near freezing
  cur <- list(
    coord = list(lon = s$Longitude, lat = s$Latitude),
    weather = list(cond),
    base = "stations",
    main = list(temp = temp, feels_like = round(temp - runif(1, 0.5, 3), 2), temp_min = round(temp - 1.2, 2),
                temp_max = round(temp + 0.9, 2), pressure = 1000 + i * 3, humidity = 70 + i * 3,
                sea_level = 1000 + i * 3, grnd_level = 995 + i * 3),
    visibility = if (cond$main == "Mist") 3500 else 10000,
    wind = list(speed = round(runif(1, 1, 9), 2), deg = 30 * i),
    clouds = list(all = c(75, 75, 0, 40, 90, 60)[i]),
    dt = now - 120 * i,
    sys = list(type = 2, id = 2000 + i, country = "GB", sunrise = now - 5 * 3600 - 60 * i,
               sunset = now + 4 * 3600 + 60 * i),
    timezone = 0, id = 2640000 + i, name = s$City, cod = 200
  )
  if (cond$main == "Rain") cur$rain <- list(`1h` = 0.42)
  if (cond$main == "Snow") cur$snow <- list(`1h` = 0.18)
  if (i %in% c(1, 3)) cur$wind$gust <- round(cur$wind$speed * 1.6, 2)
  if (i == 2) cur$weather <- list(cond, conditions[[4]])  # two conditions: the first is the primary one
  write(toJSON(cur, auto_unbox = TRUE, digits = NA), file.path(dir, sprintf("current-%s.json", s$Site.ID)))

  steps <- lapply(0:39, function(k) {
    t <- now + 3 * 3600 * (k + 1) - 12 * 3600 + 3 * 3600 * 4  # 3-hourly from 15:00 UTC
    c2 <- conditions[[(k + i) %% 5 + 1]]
    tt <- round(temp + 3 * sin(k / 8 * pi) + runif(1, -1, 1), 2)
    if (c2$main == "Snow" && tt > 2) c2 <- conditions[[2]]  # snow only when it is near freezing
    st <- list(dt = t,
               main = list(temp = tt, feels_like = round(tt - 1.5, 2), temp_min = round(tt - 0.4, 2),
                           temp_max = round(tt + 0.4, 2), pressure = 1005 + k %% 7, sea_level = 1005 + k %% 7,
                           grnd_level = 1000 + k %% 7, humidity = 60 + k %% 30, temp_kf = 0),
               weather = list(c2), clouds = list(all = (k * 13 + i * 7) %% 100),
               wind = list(speed = round(2 + (k %% 6) * 0.9, 2), deg = (k * 37) %% 360,
                           gust = round(3 + (k %% 6) * 1.4, 2)),
               visibility = 10000, pop = round(((k + i) %% 10) / 10, 1),
               sys = list(pod = if ((k %% 8) %in% 2:5) "n" else "d"),
               dt_txt = format(as.POSIXct(t, origin = "1970-01-01", tz = "UTC"), "%Y-%m-%d %H:%M:%S"))
    if (c2$main == "Rain") st$rain <- list(`3h` = 0.8)
    if (c2$main == "Snow") st$snow <- list(`3h` = 0.3)
    st
  })
  fc <- list(cod = "200", message = 0, cnt = 40, list = steps,
             city = list(id = 2640000 + i, name = s$City, coord = list(lat = s$Latitude, lon = s$Longitude),
                         country = "GB", population = 100000, timezone = 0, sunrise = now - 5 * 3600,
                         sunset = now + 4 * 3600))
  write(toJSON(fc, auto_unbox = TRUE, digits = NA), file.path(dir, sprintf("forecast-%s.json", s$Site.ID)))
}
write('{"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}',
      file.path(dir, "error-401.json"))
write('{"cod":"404","message":"city not found"}', file.path(dir, "error-404.json"))
write('{"cod":429, "message": "Your account is temporary blocked due to exceeding of requests limitation of your subscription type."}',
      file.path(dir, "error-429.json"))
