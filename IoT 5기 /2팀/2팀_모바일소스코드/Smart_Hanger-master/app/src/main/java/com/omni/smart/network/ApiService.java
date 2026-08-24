package com.omni.smart.network;

import com.omni.smart.model.Clothing;
import com.omni.smart.model.RecommendRequest;
import com.omni.smart.model.RecommendResponse;
import com.omni.smart.model.UserContext;

import com.omni.smart.model.AqiData;
import com.omni.smart.model.ForecastResponse;
import com.omni.smart.model.WeatherData;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Query;

public interface ApiService {
    @GET("api/closet")
    Call<List<Clothing>> getClothes();

    @POST("api/context")
    Call<Void> submitContext(@Body UserContext context);

    @GET("api/recommend/analyze")
    Call<RecommendResponse> getRecommendationAnalyze(
            @Query("lat") Double lat,
            @Query("lon") Double lon,
            @Query("schedule_status") String status,
            @Query("exclude_ids") List<String> excludedIds
    );

    @GET("https://api.openweathermap.org/data/2.5/weather")
    Call<WeatherData> getCurrentWeather(
            @Query("lat") double lat,
            @Query("lon") double lon,
            @Query("units") String units,
            @Query("appid") String apiKey
    );

    @GET("https://api.openweathermap.org/data/2.5/forecast")
    Call<ForecastResponse> getForecast(
            @Query("lat") double lat,
            @Query("lon") double lon,
            @Query("units") String units,
            @Query("appid") String apiKey
    );

    @GET("https://api.openweathermap.org/data/2.5/air_pollution")
    Call<AqiData> getAirPollution(
            @Query("lat") double lat,
            @Query("lon") double lon,
            @Query("appid") String apiKey
    );
}
