package com.omni.smart.viewmodel;

import android.app.Application;

import androidx.annotation.NonNull;
import androidx.lifecycle.AndroidViewModel;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;

import com.omni.smart.model.Clothing;
import com.omni.smart.model.RecommendRequest;
import com.omni.smart.model.RecommendResponse;
import com.omni.smart.model.UserContext;
import com.omni.smart.repository.ClothingRepository;

import java.util.List;

public class MainViewModel extends AndroidViewModel {
    private ClothingRepository repository;

    public MainViewModel(@NonNull Application application) {
        super(application);
        repository = new ClothingRepository();
    }

    public LiveData<List<Clothing>> getClothes() {
        return repository.getClothes();
    }

    public LiveData<Boolean> submitContext(UserContext context) {
        MutableLiveData<Boolean> result = new MutableLiveData<>();
        repository.submitContext(context, result::setValue);
        return result;
    }

    public LiveData<RecommendResponse> getRecommendation(RecommendRequest request) {
        MutableLiveData<RecommendResponse> result = new MutableLiveData<>();
        repository.getRecommendation(request, result::setValue);
        return result;
    }
}
