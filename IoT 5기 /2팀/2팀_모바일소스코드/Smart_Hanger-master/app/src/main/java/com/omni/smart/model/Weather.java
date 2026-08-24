package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;

public class Weather {
    @SerializedName("temp")
    private double temperature;
    
    @SerializedName("feels_like")
    private double feelsLike;
    
    @SerializedName("humidity")
    private int humidity;
    
    @SerializedName("wind_speed")
    private double windSpeed;
    
    @SerializedName("rain_prob")
    private int rainProbability;

    public Weather() {}

    public double getTemperature() { return temperature; }
    public void setTemperature(double temperature) { this.temperature = temperature; }

    public double getFeelsLike() { return feelsLike; }
    public void setFeelsLike(double feelsLike) { this.feelsLike = feelsLike; }

    public int getHumidity() { return humidity; }
    public void setHumidity(int humidity) { this.humidity = humidity; }

    public double getWindSpeed() { return windSpeed; }
    public void setWindSpeed(double windSpeed) { this.windSpeed = windSpeed; }

    public int getRainProbability() { return rainProbability; }
    public void setRainProbability(int rainProbability) { this.rainProbability = rainProbability; }
}
