package com.omni.smart.viewmodel;

import android.app.Application;
import android.location.Location;

import androidx.annotation.NonNull;
import androidx.lifecycle.AndroidViewModel;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;
import androidx.lifecycle.Transformations;

import com.omni.smart.model.AqiData;
import com.omni.smart.model.ForecastResponse;
import com.omni.smart.model.UserContext;
import com.omni.smart.model.WeatherData;
import com.omni.smart.repository.ClothingRepository;
import com.omni.smart.repository.WeatherRepository;
import com.omni.smart.util.GeocodingHelper;
import com.omni.smart.util.LocationHelper;

import java.util.List;

public class HomeViewModel extends AndroidViewModel {
    private final WeatherRepository weatherRepository;
    private final ClothingRepository clothingRepository;
    private final LocationHelper locationHelper;
    private final MutableLiveData<Location> lastLocation = new MutableLiveData<>();
    private final MutableLiveData<Boolean> syncStatus = new MutableLiveData<>();
    // 위치 텍스트는 날씨 API 성공 여부와 무관하게 독립적으로 갱신됨
    private final MutableLiveData<String> address = new MutableLiveData<>("위치 찾는 중...");

    public HomeViewModel(@NonNull Application application) {
        super(application);
        weatherRepository = new WeatherRepository();
        clothingRepository = new ClothingRepository();
        locationHelper = new LocationHelper(application);
    }

    public void refreshLocation() {
        locationHelper.getLastLocation(location -> {
            if (location != null) {
                lastLocation.setValue(location);
                // 위치를 받자마자 바로 역지오코딩 시작 (날씨 API 응답을 기다리지 않음)
                GeocodingHelper.getAddressFromLocation(
                        getApplication(),
                        location.getLatitude(),
                        location.getLongitude(),
                        result -> address.setValue(result)
                );
            } else {
                address.setValue("위치를 가져올 수 없습니다");
            }
        });
    }

    public LiveData<String> getAddress() {
        return address;
    }

    public void syncContextToServer(WeatherData weather, AqiData aqi, String status, List<UserContext.ScheduleItem> scheduleItems) {
        Location location = lastLocation.getValue();
        if (location == null) return;

        UserContext context = new UserContext();
        context.setLatitude(location.getLatitude());
        context.setLongitude(location.getLongitude());
        context.setScheduleStatus(status != null ? status : "free");

        if (weather != null) {
            context.setWeather(weather.getCondition());
        }

        if (aqi != null) {
            context.setAqi(aqi.getAqi());
        }

        if (scheduleItems != null) {
            context.setSchedule(scheduleItems);
        }

        clothingRepository.submitContext(context, success -> syncStatus.postValue(success));
    }

    public LiveData<Boolean> getSyncStatus() {
        return syncStatus;
    }

    public LiveData<WeatherData> getCurrentWeather() {
        return Transformations.switchMap(lastLocation, location ->
                weatherRepository.getCurrentWeather(location.getLatitude(), location.getLongitude())
        );
    }

    public LiveData<ForecastResponse> getForecast() {
        return Transformations.switchMap(lastLocation, location ->
                weatherRepository.getForecast(location.getLatitude(), location.getLongitude())
        );
    }

    public LiveData<AqiData> getAirPollution() {
        return Transformations.switchMap(lastLocation, location ->
                weatherRepository.getAirPollution(location.getLatitude(), location.getLongitude())
        );
    }

    public LiveData<Location> getLocation() {
        return lastLocation;
    }
}