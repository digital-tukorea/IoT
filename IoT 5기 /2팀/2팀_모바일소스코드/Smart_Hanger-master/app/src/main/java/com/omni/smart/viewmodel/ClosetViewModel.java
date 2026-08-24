package com.omni.smart.viewmodel;

import android.app.Application;

import androidx.annotation.NonNull;
import androidx.lifecycle.AndroidViewModel;
import androidx.lifecycle.LiveData;

import com.omni.smart.model.Clothing;
import com.omni.smart.repository.ClothingRepository;

import java.util.List;

public class ClosetViewModel extends AndroidViewModel {
    private ClothingRepository repository;

    public ClosetViewModel(@NonNull Application application) {
        super(application);
        repository = new ClothingRepository();
    }

    public LiveData<List<Clothing>> getClothes() {
        return repository.getClothes();
    }
}
