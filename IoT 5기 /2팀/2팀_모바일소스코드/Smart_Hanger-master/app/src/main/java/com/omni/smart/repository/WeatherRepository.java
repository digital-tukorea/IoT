package com.omni.smart.repository;

import android.util.Log;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;

import com.omni.smart.model.AqiData;
import com.omni.smart.model.ForecastResponse;
import com.omni.smart.model.WeatherData;
import com.omni.smart.network.ApiService;
import com.omni.smart.network.RetrofitClient;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class WeatherRepository {
    private static final String TAG = "WeatherRepository";
    private ApiService apiService;
    // Known working public API keys for OpenWeatherMap (replace with yours if needed)
    private static final String API_KEY = "61fa8d37c7bef210fce2c04194d8f46f";

    public WeatherRepository() {
        apiService = RetrofitClient.getClient().create(ApiService.class);
    }

    public LiveData<WeatherData> getCurrentWeather(double lat, double lon) {
        MutableLiveData<WeatherData> data = new MutableLiveData<>();
        Log.d(TAG, "Fetching weather for: " + lat + ", " + lon);
        apiService.getCurrentWeather(lat, lon, "metric", API_KEY).enqueue(new Callback<WeatherData>() {
            @Override
            public void onResponse(Call<WeatherData> call, Response<WeatherData> response) {
                if (response.isSuccessful() && response.body() != null) {
                    Log.d(TAG, "Weather fetched successfully: " + response.body().getCityName());
                    data.setValue(response.body());
                } else {
                    Log.e(TAG, "Weather fetch failed: " + response.code() + " " + response.message());
                    data.setValue(null);
                }
            }

            @Override
            public void onFailure(Call<WeatherData> call, Throwable t) {
                Log.e(TAG, "Weather fetch error: " + t.getMessage());
                data.setValue(null);
            }
        });
        return data;
    }

    public LiveData<ForecastResponse> getForecast(double lat, double lon) {
        MutableLiveData<ForecastResponse> data = new MutableLiveData<>();
        apiService.getForecast(lat, lon, "metric", API_KEY).enqueue(new Callback<ForecastResponse>() {
            @Override
            public void onResponse(Call<ForecastResponse> call, Response<ForecastResponse> response) {
                if (response.isSuccessful()) {
                    data.setValue(response.body());
                } else {
                    data.setValue(null);
                }
            }

            @Override
            public void onFailure(Call<ForecastResponse> call, Throwable t) {
                data.setValue(null);
            }
        });
        return data;
    }

    public LiveData<AqiData> getAirPollution(double lat, double lon) {
        MutableLiveData<AqiData> data = new MutableLiveData<>();
        apiService.getAirPollution(lat, lon, API_KEY).enqueue(new Callback<AqiData>() {
            @Override
            public void onResponse(Call<AqiData> call, Response<AqiData> response) {
                if (response.isSuccessful()) {
                    data.setValue(response.body());
                } else {
                    data.setValue(null);
                }
            }

            @Override
            public void onFailure(Call<AqiData> call, Throwable t) {
                data.setValue(null);
            }
        });
        return data;
    }
}
