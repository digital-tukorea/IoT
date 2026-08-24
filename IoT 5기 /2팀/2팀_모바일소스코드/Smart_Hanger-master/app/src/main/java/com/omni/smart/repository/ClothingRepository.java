package com.omni.smart.repository;

import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;

import com.omni.smart.model.Clothing;
import com.omni.smart.model.RecommendRequest;
import com.omni.smart.model.RecommendResponse;
import com.omni.smart.model.UserContext;
import com.omni.smart.network.ApiService;
import com.omni.smart.network.RetrofitClient;

import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ClothingRepository {
    private ApiService apiService;

    public interface ResultCallback<T> {
        void onResult(T result);
    }

    public ClothingRepository() {
        apiService = RetrofitClient.getClient().create(ApiService.class);
    }

    public LiveData<List<Clothing>> getClothes() {
        MutableLiveData<List<Clothing>> data = new MutableLiveData<>();
        apiService.getClothes().enqueue(new Callback<List<Clothing>>() {
            @Override
            public void onResponse(Call<List<Clothing>> call, Response<List<Clothing>> response) {
                if (response.isSuccessful()) {
                    List<Clothing> body = response.body();
                    if (body != null) {
                        body.sort((a, b) -> {
                            int idA = Integer.parseInt(a.getId());
                            int idB = Integer.parseInt(b.getId());
                            return Integer.compare(idA, idB);
                        });

                        android.util.Log.d("ClothingRepository", "Fetched clothes count: " + body.size());
                        if (!body.isEmpty()) {
                            Clothing first = body.get(0);
                            android.util.Log.d("ClothingRepository", "First item - ID: " + first.getId() + ", Name: " + first.getName() + ", Path: " + first.getImageUrl());
                        }
                    }
                    data.setValue(body);
                } else {
                    android.util.Log.e("ClothingRepository", "Failed to fetch clothes: " + response.code() + " " + response.message());
                    data.setValue(null);
                }
            }

            @Override
            public void onFailure(Call<List<Clothing>> call, Throwable t) {
                data.setValue(null);
            }
        });
        return data;
    }

    // LiveData 관찰자가 없는 곳(예: BroadcastReceiver)에서
    // 옷 목록을 단발성으로 가져오기 위한 콜백 방식 메서드
    public void getClothesOnce(ResultCallback<List<Clothing>> callback) {
        apiService.getClothes().enqueue(new Callback<List<Clothing>>() {
            @Override
            public void onResponse(Call<List<Clothing>> call, Response<List<Clothing>> response) {
                if (callback != null) {
                    List<Clothing> body = response.isSuccessful() ? response.body() : null;
                    if (body != null) {
                        body.sort((a, b) -> {
                            int idA = Integer.parseInt(a.getId());
                            int idB = Integer.parseInt(b.getId());
                            return Integer.compare(idA, idB);
                        });
                    }
                    callback.onResult(body);
                }
            }

            @Override
            public void onFailure(Call<List<Clothing>> call, Throwable t) {
                if (callback != null) {
                    callback.onResult(null);
                }
            }
        });
    }

    public void submitContext(UserContext context, ResultCallback<Boolean> callback) {
        apiService.submitContext(context).enqueue(new Callback<Void>() {
            @Override
            public void onResponse(Call<Void> call, Response<Void> response) {
                if (callback != null) {
                    callback.onResult(response.isSuccessful());
                }
            }

            @Override
            public void onFailure(Call<Void> call, Throwable t) {
                if (callback != null) {
                    callback.onResult(false);
                }
            }
        });
    }

    public void getRecommendation(RecommendRequest request, ResultCallback<RecommendResponse> callback) {
        apiService.getRecommendationAnalyze(
                request.getContext().getLatitude(),
                request.getContext().getLongitude(),
                request.getContext().getScheduleStatus(),
                request.getExcludedIds()
        ).enqueue(new Callback<RecommendResponse>() {
            @Override
            public void onResponse(Call<RecommendResponse> call, Response<RecommendResponse> response) {
                if (callback != null) {
                    if (response.isSuccessful()) {
                        callback.onResult(response.body());
                    } else {
                        callback.onResult(null);
                    }
                }
            }

            @Override
            public void onFailure(Call<RecommendResponse> call, Throwable t) {
                if (callback != null) {
                    callback.onResult(null);
                }
            }
        });
    }
}